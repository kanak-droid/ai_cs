"""Owns every write to Ticket.status and TicketStatusHistory.

This is the ONLY module allowed to mutate ticket status. `_record_status`
inserts the history row and mirrors `ticket.status` in the same transaction,
so the two can never diverge — there is deliberately no other way to change a
ticket's status (no DB trigger, no ORM event hook; see the build plan for why).
"""

import logging
from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.core.time import utcnow
from app.integrations import (
    admin_mapping_client,
    cs_assignment_client,
    moengage_client,
    queue_performance_client,
    slack_client,
    zoho_client,
)
from app.models.admin import Admin
from app.models.astrologer import Astrologer
from app.models.enums import ADMIN_SETTABLE_STATUSES, AdminRole, TicketStatus
from app.models.ticket import Ticket
from app.models.ticket_status_history import TicketStatusHistory
from app.services import chat_session_service

logger = logging.getLogger(__name__)

# A resolved ticket the astrologer never responds to (satisfied/unsatisfied)
# auto-closes after this long. Shortened from 5 days to 48 hours (2026-08-20)
# to match the astrologer-facing "resolved" chat notification's own 48h
# window (see chat-app's persisted ticket-status tracking) — after that, no
# response is treated the same as a quiet confirmation. Checked lazily on
# read (here, and in scripts/auto_close_resolved_tickets.py for anyone who
# wants real promptness via an external cron), not a background job, since
# nothing else in this app runs on a schedule.
_AUTO_CLOSE_AFTER = timedelta(hours=48)

# Which team a ticket routes to for the Slack escalation notification — derived
# from category rather than a separate DB column, so this can change without a
# migration. Anything not explicitly a tech issue is treated as business.
_TECH_CATEGORIES = {"technical", "other"}
_TEAM_EMOJI = {"tech": "🛠️", "business": "💼"}

# Priority 1/2 astrologers ("P1"/"P2") get white-glove routing — their KAM is
# cc'd directly in the Slack notification rather than staying silent. Everyone
# else (P3+, or unknown/unlinked) goes through the standard CS flow. Uses the
# same queue_performance_client the get_priority_ranking tool uses (mock
# fallback included) so a ticket's routing never disagrees with whatever
# priority the model already told the astrologer in chat.
_VIP_PRIORITY_MAX = 2

# Categories a CS always owns at creation, regardless of priority — the
# astrologer's personal KAM still gets set as assigned_admin_id (so their
# name shows in the dashboard like any other ticket) and, for a VIP
# astrologer, still gets @mentioned in the Slack notification for
# visibility, but the ticket never counts as kam_notified ("in their name")
# until a CS actually escalates it (see escalate_to_kam) — that's the only
# path back to a KAM for these categories now. 2026-08-25 policy change:
# "no_visibility" and "profile" used to route straight to the KAM's own
# Slack channel instead of through CS (the former only for VIP, the latter
# always, with CS never looped in at all for it); "technical"/
# "phone_change"/"payout"/"kyc" used to still tag the KAM as notified for a
# VIP astrologer even though they were never treated as direct-to-KAM
# categories. All now unified under the same CS-first routing.
_CS_ONLY_CATEGORIES = {"technical", "no_visibility", "profile", "phone_change", "payout", "kyc"}

# "Referral amount" (an astrologer chasing a referral bonus they're owed)
# always goes straight to their KAM, CS never looped in at all, regardless
# of priority — same exclusivity "profile" used to have before the
# 2026-08-25 change, just for a different category.
_ALWAYS_KAM_ONLY_CATEGORIES = {"referral_amount"}

# "Resignation" is the one category with its own, wider priority cutoff —
# P1-P3 (not just P1/P2 like _VIP_PRIORITY_MAX elsewhere) go straight to the
# KAM, CS excluded entirely; P4/P5 or unranked go to CS instead, KAM
# excluded. Never both at once, unlike the general is_vip cc pattern below.
_RESIGNATION_KAM_PRIORITY_MAX = 3


def _team_for_category(category: str) -> str:
    return "tech" if category.strip().lower() in _TECH_CATEGORIES else "business"


def astrologer_priority(db: Session, astrologer_id: int) -> int | None:
    return queue_performance_client.get_queue_performance(db, astrologer_id).priority


def routing_for_ticket(category: str, priority: int | None) -> tuple[bool, bool]:
    """(kam_notified, cs_notified) for a ticket with this category/
    priority — the single source of truth create_ticket and
    scripts/backfill_ticket_notified.py both use, so the stored flags can
    never drift from the actual routing decision.

    Three shapes, depending on category:
    - _ALWAYS_KAM_ONLY_CATEGORIES ("referral_amount"): always (True, False)
      — KAM owns it, CS excluded, regardless of priority.
    - "resignation": mutually exclusive by its own priority cutoff — P1-P3
      is (True, False) (KAM owns it, CS excluded), P4/P5/unranked is
      (False, True) (CS owns it, KAM excluded).
    - Everything else: cs_notified is unconditionally True (every other
      category loops in a CS at creation) and kam_notified is True for a
      VIP astrologer (P1/P2) UNLESS the category is in
      _CS_ONLY_CATEGORIES, which never notifies the KAM at creation
      regardless of priority — only escalate_to_kam can do that for those.
    """
    normalized = category.strip().lower()
    is_vip = priority is not None and priority <= _VIP_PRIORITY_MAX

    if normalized in _ALWAYS_KAM_ONLY_CATEGORIES:
        return True, False
    if normalized == "resignation":
        kam_owns = priority is not None and priority <= _RESIGNATION_KAM_PRIORITY_MAX
        return kam_owns, not kam_owns

    kam_notified = is_vip and normalized not in _CS_ONLY_CATEGORIES
    return kam_notified, True


def is_vip_priority(db: Session, astrologer_id: int) -> bool:
    priority = astrologer_priority(db, astrologer_id)
    # Unranked (None) is deliberately never VIP — see QueuePerformance.priority.
    return priority is not None and priority <= _VIP_PRIORITY_MAX


# Technical/business issues (+ Photo Change) need photo/video evidence before
# escalating — at every priority level (2026-08-13 policy: evidence is
# required for everyone; priority only changes whether the bot analyzes it —
# see CREATE_SUPPORT_TICKET's description and prompt.py). For "profile"
# specifically this is the astrologer's original uploaded photo (the n8n
# beautify step is on hold, 2026-08-14 — see docs/chatbot-approach.md §8d).
_EVIDENCE_REQUIRED_CATEGORIES = {"technical", "other", "payout", "kyc", "profile"}


def needs_evidence(category: str) -> bool:
    return category.strip().lower() in _EVIDENCE_REQUIRED_CATEGORIES


_TERMINAL_STATUSES = (TicketStatus.RESOLVED, TicketStatus.CLOSED)


def get_active_ticket_for_category(db: Session, astrologer_id: int, category: str) -> Ticket | None:
    """Most recent still-open (not resolved/closed) ticket this astrologer
    already has for this category, if any — used to stop a duplicate ticket
    for the same problem while one is already in the queue (see
    tool_registry._handle_create_support_ticket). A resolved-but-not-yet-
    auto-closed ticket (§7a) doesn't count as active here — RESOLVED is
    already excluded regardless of whether the 5-day auto-close has actually
    run yet."""
    stmt = (
        select(Ticket)
        .where(
            Ticket.astrologer_id == astrologer_id,
            func.lower(Ticket.category) == category.strip().lower(),
            Ticket.status.not_in(_TERMINAL_STATUSES),
        )
        .order_by(Ticket.created_at.desc())
    )
    return db.scalars(stmt).first()


def _slack_mention(admin: Admin | None, fallback_name: str) -> str:
    """`<@SLACK_USER_ID>` is the only syntax Slack actually renders as a
    highlighted, notifying mention — plain "@name" text in an incoming
    webhook message is never converted into one, so it silently never
    pinged anyone. Falls back to plain text (still readable, just not a
    real mention) for admins with no slack_user_id on file yet.
    """
    if admin and admin.slack_user_id:
        return f"<@{admin.slack_user_id}>"
    return f"@{fallback_name}"


def _record_status(
    db: Session, ticket: Ticket, status: TicketStatus, *, changed_by: str, note: str | None = None
) -> None:
    db.add(TicketStatusHistory(ticket_id=ticket.id, status=status, changed_by=changed_by, note=note))
    ticket.status = status
    if status == TicketStatus.RESOLVED:
        # Fresh resolution — start (or restart, after a reopen) the
        # satisfaction-response clock, and clear any rating/satisfaction
        # left over from an earlier resolve/reopen cycle on this same ticket.
        ticket.resolved_at = utcnow()
        ticket.satisfaction = None
        ticket.rating = None
        ticket.rating_reasons = None
        ticket.rating_comment = None
        ticket.rated_at = None

    # Fire-and-forget: lets MoEngage's own campaigns decide which status
    # changes actually push a notification to the astrologer. This is the
    # one call site for every status write in the app, so nothing needs its
    # own notify call — but exactly because of that, a bug or outage here
    # must never take down a real status transition, hence the belt-and-
    # suspenders try/except even though moengage_client already catches its
    # own network errors internally.
    try:
        moengage_client.send_ticket_status_event(
            ticket, new_status=status.value, changed_by=changed_by, note=note
        )
    except Exception:
        logger.exception("MoEngage event dispatch raised unexpectedly for ticket #%s", ticket.id)

    # Same reasoning, same belt-and-suspenders wrapping — keep an already-
    # pushed Zoho Desk ticket's status in sync. No-ops (inside zoho_client)
    # for a ticket that was never pushed (zoho_ticket_id is None).
    if ticket.zoho_ticket_id is not None:
        try:
            zoho_client.update_status(ticket.zoho_ticket_id, zoho_client.zoho_status_for(ticket))
        except Exception:
            logger.exception("Zoho Desk status sync raised unexpectedly for ticket #%s", ticket.id)


def _maybe_push_to_zoho(db: Session, ticket: Ticket) -> None:
    """Pushes a ticket into Zoho Desk the first time it becomes cs_notified
    — either right after creation, or later via reassign_ticket flipping
    cs_notified True for a ticket that started without a CS (e.g. a
    'profile' category ticket). No-ops if already pushed or still not
    cs_notified. Same safety requirement as every other integration call
    here: a Zoho outage must never block the ticket write it's attached to.
    """
    if ticket.zoho_ticket_id is not None or not ticket.cs_notified:
        return
    try:
        ticket.zoho_ticket_id = zoho_client.create_ticket(db, ticket)
    except Exception:
        logger.exception("Zoho Desk ticket creation raised unexpectedly for ticket #%s", ticket.id)
        return

    if ticket.zoho_ticket_id is not None and ticket.attachment_url:
        try:
            zoho_client.upload_attachment(ticket.zoho_ticket_id, ticket.attachment_url)
        except Exception:
            logger.exception("Zoho Desk attachment upload raised unexpectedly for ticket #%s", ticket.id)


def backfill_push_to_zoho(db: Session, ticket: Ticket) -> bool:
    """Public entry point for scripts/backfill_zoho_tickets.py — a ticket
    created before the Zoho sync existed never went through create_ticket
    or reassign_ticket, so it needs an explicit one-time push. Same guard
    and logic as _maybe_push_to_zoho, exposed here so the one-off script
    doesn't reach into a private function. Returns whether the push
    actually left the ticket with a zoho_ticket_id, so the caller can
    report a real pushed/failed count instead of assuming success.
    """
    _maybe_push_to_zoho(db, ticket)
    return ticket.zoho_ticket_id is not None


def sync_chat_transcript_to_zoho(db: Session, ticket: Ticket, session_id: str | None) -> None:
    """Posts the astrologer's full chat transcript (see
    chat_session_service.get_transcript_text) as a Zoho ticket comment —
    separate from the ticket's own short AI-written description, so
    whoever works the ticket has the complete back-and-forth one click
    away. Called by the tool handler right after create_ticket AND
    chat_session_service.mark_escalated both return (the ChatSession ->
    Ticket link isn't set until mark_escalated runs, and this doesn't
    strictly need it anyway — session_id alone is enough to find the
    messages). No-ops if the ticket was never pushed to Zoho, or there's
    no transcript to send. Best-effort, same as every other Zoho call.
    """
    if ticket.zoho_ticket_id is None:
        return
    transcript = chat_session_service.get_transcript_text(db, session_id)
    if not transcript:
        return
    try:
        zoho_client.post_comment(ticket.zoho_ticket_id, transcript)
    except Exception:
        logger.exception("Zoho Desk transcript post raised unexpectedly for ticket #%s", ticket.id)


def _log_note(db: Session, ticket: Ticket, *, changed_by: str, note: str) -> None:
    """Records a history row for an event that isn't a status transition
    (reassignment, escalation) — logs the ticket's CURRENT status verbatim
    rather than calling _record_status, which must never be used here: on a
    RESOLVED ticket it would reset resolved_at to now and wipe satisfaction,
    which a mere ownership/escalation change must never trigger.
    """
    db.add(TicketStatusHistory(ticket_id=ticket.id, status=ticket.status, changed_by=changed_by, note=note))


def create_ticket(
    db: Session,
    *,
    astrologer_id: int,
    category: str,
    sub_category: str,
    description: str,
    description_en: str,
    preferred_language: str,
    attachment_url: str | None = None,
) -> Ticket:
    """Create a ticket, then auto-assign it and notify Slack — all in one transaction.

    This cross-integration sequencing (create -> assign -> notify) belongs here,
    not in the agent or in a route handler.
    """
    ticket = Ticket(
        astrologer_id=astrologer_id,
        category=category,
        sub_category=sub_category,
        description=description,
        description_en=description_en,
        preferred_language=preferred_language,
        attachment_url=attachment_url,
        status=TicketStatus.SUBMITTED,
    )
    db.add(ticket)
    db.flush()  # assigns ticket.id

    _record_status(db, ticket, TicketStatus.SUBMITTED, changed_by="system", note="Ticket submitted")

    assignment = admin_mapping_client.get_assigned_admin(db, astrologer_id)
    ticket.assigned_admin_id = assignment.admin_id
    _record_status(
        db,
        ticket,
        TicketStatus.ASSIGNED_TO_KAM,
        changed_by="system",
        note=f"Auto-assigned to admin #{assignment.admin_id}",
    )

    astrologer = db.get(Astrologer, astrologer_id)
    cs_assignment = cs_assignment_client.get_assigned_cs(
        db, ticket_id=ticket.id, astrologer_language=astrologer.language if astrologer else ""
    )
    if cs_assignment is not None:
        ticket.assigned_cs_id = cs_assignment.admin_id

    admin = db.get(Admin, assignment.admin_id)
    cs_admin = db.get(Admin, cs_assignment.admin_id) if cs_assignment else None
    team = _team_for_category(category)
    kam_name = admin.name if admin else "KAM"
    cs_name = cs_admin.name if cs_admin else None
    normalized_category = category.strip().lower()
    priority = astrologer_priority(db, astrologer_id)
    is_vip = priority is not None and priority <= _VIP_PRIORITY_MAX

    kam_notified, cs_notified = routing_for_ticket(category, priority)

    # Persisted so the dashboard's "assigned to me" filter can tell "this
    # admin was actually routed/notified" apart from "this is merely the
    # astrologer's regular KAM/language-matched CS" — see the Ticket model.
    ticket.kam_notified = kam_notified
    ticket.cs_notified = cs_notified

    priority_label = f"P{priority}" if priority is not None else "Unranked"
    expert_id_label = astrologer.expert_id if astrologer and astrologer.expert_id else "not linked"
    astrologer_name = astrologer.name if astrologer else "Unknown"

    header = f"{_TEAM_EMOJI.get(team, '🎫')} *New ticket #{ticket.id}*"
    body = (
        f"*Category:* {category} / {sub_category}\n"
        f"*Team:* {team} team\n"
        f"*Astrologer:* {astrologer_name} (#{astrologer_id}, expert_id: {expert_id_label}) — "
        f"Priority: {priority_label}\n"
        f"<{settings.ADMIN_DASHBOARD_URL}/tickets/{ticket.id}|View in dashboard>"
    )
    cs_line = (
        f"\n*CS:* {_slack_mention(cs_admin, cs_name)} ({'/'.join(cs_admin.languages) or 'no language set'})"
        if cs_name and ticket.cs_notified
        else ""
    )

    # Every ticket now posts to the shared support channel — there's no
    # separate "the KAM's own personal channel" anymore (none of the real
    # KAMs had ever actually set one — see the removed direct_to_kam
    # branch's history).
    if kam_notified and not cs_notified:
        # Genuinely KAM-owned, CS excluded entirely — only
        # _ALWAYS_KAM_ONLY_CATEGORIES ("referral_amount", always) or
        # "resignation" at P1-P3 ever reach this, per routing_for_ticket.
        reason = "referral amount request" if normalized_category == "referral_amount" else "resignation"
        text = (
            f"{header}\n{body}\n*Routed directly to {_slack_mention(admin, kam_name)} "
            f"as their KAM ({reason}).*"
        )
    elif is_vip:
        # VIP astrologer: KAM explicitly cc'd for visibility — even on a
        # CS-only category (kam_notified=False), so the KAM still sees it
        # and can pick it up personally, without it ever landing "in their
        # name" unless a CS actually escalates it.
        text = (
            f"{header}\n{body}\n*KAM:* {_slack_mention(admin, kam_name)} "
            f"(priority astrologer — please loop in){cs_line}"
        )
    else:
        # Standard CS routing — KAM stays the internal assignee but isn't
        # specially paged for a non-priority astrologer's ticket.
        text = f"{header}\n{body}{cs_line}"

    slack_client.post_message(db, channel=settings.SLACK_SUPPORT_CHANNEL, text=text, ticket_id=ticket.id)
    if attachment_url:
        # Best-effort — pushes the actual photo/video into Slack (see
        # upload_attachment's docstring for why); never blocks ticket
        # creation if it fails.
        slack_client.upload_attachment(db, attachment_url=attachment_url, ticket_id=ticket.id)

    _maybe_push_to_zoho(db, ticket)

    db.commit()
    db.refresh(ticket)
    return ticket


def transition_status(
    db: Session, ticket: Ticket, new_status: TicketStatus, *, changed_by: str, note: str | None = None
) -> Ticket:
    """The only entry point for an admin manually moving a ticket's status
    from the dashboard — enforces two rules specific to a MANUAL admin
    action (the system/astrologer-driven paths in this module call
    _record_status directly and are deliberately exempt):

    - only ADMIN_SETTABLE_STATUSES is reachable this way — CLOSED isn't
      (see that constant's docstring); nothing enforced this before
      2026-08-20 even though the frontend dropdown already only offered
      those options, so a direct API call could bypass it.
    - RESOLVED requires a real, non-blank note — it's what actually
      reaches the astrologer as the explanation of what was fixed (see the
      chat-app's status-change notification), so a blank one would leave
      them with nothing to read.
    """
    if new_status not in ADMIN_SETTABLE_STATUSES:
        raise AppError(f"'{new_status.value}' can't be set manually.")
    if new_status == TicketStatus.RESOLVED and not (note and note.strip()):
        raise AppError("A comment is required when marking a ticket resolved.")

    _record_status(db, ticket, new_status, changed_by=changed_by, note=note)
    db.commit()
    db.refresh(ticket)
    return ticket


def reassign_ticket(
    db: Session,
    ticket: Ticket,
    *,
    role: str,
    new_admin_id: int,
    changed_by: str,
    note: str | None = None,
) -> Ticket:
    """Manually moves ownership of a ticket's KAM or CS to a different
    admin of that role — e.g. covering for someone on leave, or correcting
    a bad round-robin pick. Validates the target is a real, currently-
    assignable admin of the requested role (active, not on leave, correct
    role) so a ticket can never end up pointed at someone who can't
    actually work it — the exact same eligibility bar as new-ticket
    round-robin (admin_mapping_client/cs_assignment_client).

    Does NOT go through _record_status/transition_status — ownership isn't
    a status transition, and calling that on a RESOLVED ticket would wipe
    resolved_at/satisfaction as a side effect (see _record_status). Sets
    kam_notified/cs_notified so the new owner's queue picks it up.
    """
    if role not in ("kam", "cs"):
        raise AppError("role must be 'kam' or 'cs'")
    target_role = AdminRole.KAM if role == "kam" else AdminRole.CS

    new_admin = db.get(Admin, new_admin_id)
    if new_admin is None or new_admin.role != target_role:
        raise AppError(f"Admin {new_admin_id} is not an active {role.upper()}")
    if not new_admin.is_active or new_admin.is_temporarily_inactive:
        raise AppError(f"{new_admin.name} isn't currently assignable (inactive or on leave)")

    if role == "kam":
        ticket.assigned_admin_id = new_admin.id
        ticket.kam_notified = True
    else:
        ticket.assigned_cs_id = new_admin.id
        ticket.cs_notified = True

    log_line = f"Reassigned {role.upper()} to {new_admin.name}"
    if note:
        log_line += f" — {note}"
    _log_note(db, ticket, changed_by=changed_by, note=log_line)

    if role == "cs":
        # Covers a ticket that started without a CS (e.g. 'profile'
        # category, never pushed at creation) and is only now being handed
        # to one — create_ticket's own agent-matching already assigns the
        # right owner in this case.
        _maybe_push_to_zoho(db, ticket)
        # Already-pushed ticket handed to a DIFFERENT CS — the Zoho ticket
        # still shows the old owner unless we explicitly update it (a
        # status change alone, via _record_status, never touches assignee).
        if ticket.zoho_ticket_id is not None:
            agent_id = zoho_client.find_agent_id_by_email(new_admin.email)
            if agent_id:
                try:
                    zoho_client.update_assignee(ticket.zoho_ticket_id, agent_id)
                except Exception:
                    logger.exception(
                        "Zoho Desk assignee update raised unexpectedly for ticket #%s", ticket.id
                    )

    db.commit()
    db.refresh(ticket)
    return ticket


def escalate_to_kam(db: Session, ticket: Ticket, *, changed_by: str, note: str) -> Ticket:
    """A CS handing this ticket off to its KAM — e.g. it needs the KAM's
    personal relationship with the astrologer, or is beyond what CS can
    resolve alone. Ensures the KAM is actually notified (kam_notified=True,
    same flag the ticket queue's "assigned to me" filter checks) and flags
    escalated_to_kam so analytics can exclude this ticket from the CS's
    "resolved" tally even though assigned_cs_id never changes — the CS
    stays associated for reference, the KAM is who actually resolves it
    (see analytics_service._get_kam_performance). A comment is mandatory:
    escalating with no explanation just leaves the KAM guessing.

    Does not change ticket.status — same reasoning as reassign_ticket (see
    _log_note): this is a handoff, not a status transition, and must never
    risk _record_status's RESOLVED side effect.
    """
    if not note or not note.strip():
        raise AppError("A comment is required to escalate this ticket.")
    if ticket.assigned_admin_id is None:
        raise AppError("This ticket has no KAM assigned to escalate to.")

    ticket.kam_notified = True
    ticket.escalated_to_kam = True
    ticket.escalated_at = utcnow()
    _log_note(db, ticket, changed_by=changed_by, note=f"Escalated to KAM — {note.strip()}")

    # Escalation isn't a status transition, so it never goes through
    # _record_status's own Zoho status-sync call — push the "Escalated"
    # status directly here instead. _maybe_push_to_zoho first, in case this
    # ticket was somehow never pushed at all (defensive; escalation is
    # normally a CS action on an already-cs_notified, already-pushed ticket).
    _maybe_push_to_zoho(db, ticket)
    if ticket.zoho_ticket_id is not None:
        try:
            zoho_client.update_status(ticket.zoho_ticket_id, zoho_client.zoho_status_for(ticket))
        except Exception:
            logger.exception("Zoho Desk escalation status sync raised unexpectedly for ticket #%s", ticket.id)

    db.commit()
    db.refresh(ticket)
    return ticket


def record_ticket_rating(
    db: Session, ticket: Ticket, *, rating: int, reasons: list[str], comment: str | None
) -> Ticket:
    """The astrologer's 1-5 star rating of a resolved ticket, from the chat
    webview or the tickets page. The score itself decides what used to be a
    separate satisfied/unsatisfied click: >=4 closes the ticket out, <=3
    reopens it (back to under_review, so it lands in the KAM's queue again)
    rather than leaving it "resolved" when the astrologer says it isn't —
    the bot then asks what's still wrong. `reasons` is whichever preset list
    the frontend showed for that score band (positive or negative); both it
    and `comment` are stored as-is, no validation on their contents.
    """
    if ticket.status != TicketStatus.RESOLVED:
        raise AppError("This ticket isn't awaiting a rating.")

    satisfied = rating >= 4
    ticket.rating = rating
    ticket.rating_reasons = reasons
    ticket.rating_comment = comment
    ticket.rated_at = utcnow()
    ticket.satisfaction = "satisfied" if satisfied else "unsatisfied"
    if satisfied:
        _record_status(db, ticket, TicketStatus.CLOSED, changed_by="astrologer", note="Confirmed resolved")
    else:
        _record_status(
            db,
            ticket,
            TicketStatus.UNDER_REVIEW,
            changed_by="astrologer",
            note="Marked unsatisfied — reopened",
        )
    db.commit()
    db.refresh(ticket)
    return ticket


def _maybe_auto_close_stale(db: Session, ticket: Ticket) -> Ticket:
    if (
        ticket.status == TicketStatus.RESOLVED
        and ticket.satisfaction is None
        and ticket.resolved_at is not None
        and utcnow() - ticket.resolved_at > _AUTO_CLOSE_AFTER
    ):
        _record_status(
            db,
            ticket,
            TicketStatus.CLOSED,
            changed_by="system",
            note="Auto-closed — no astrologer response after 48 hours",
        )
        db.commit()
        db.refresh(ticket)
    return ticket


def auto_close_stale_resolved_tickets(db: Session) -> list[Ticket]:
    """Batch version of _maybe_auto_close_stale, for an external cron/
    scheduled job (see scripts/auto_close_resolved_tickets.py, same
    invocation shape as scripts/sync_sheets.py) — the lazy, checked-on-read
    version above only closes a ticket once someone happens to load it
    after the cutoff, which in practice is reliable (both the astrologer's
    chat and the admin dashboard read through get_ticket/list_all_tickets
    regularly) but not a hard real-time guarantee. This closes every
    eligible ticket in one pass regardless of whether anyone's looking, for
    anyone who wants that stronger guarantee.
    """
    cutoff = utcnow() - _AUTO_CLOSE_AFTER
    stmt = select(Ticket).where(
        Ticket.status == TicketStatus.RESOLVED,
        Ticket.satisfaction.is_(None),
        Ticket.resolved_at.isnot(None),
        Ticket.resolved_at < cutoff,
    )
    tickets = list(db.scalars(stmt).all())
    for ticket in tickets:
        _record_status(
            db,
            ticket,
            TicketStatus.CLOSED,
            changed_by="system",
            note="Auto-closed — no astrologer response after 48 hours",
        )
    db.commit()
    for ticket in tickets:
        db.refresh(ticket)
    return tickets


def get_ticket(db: Session, ticket_id: int) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    # Checked here (not just on the astrologer-facing path) so an admin
    # viewing a ticket also sees a correctly-closed status, regardless of
    # whether the astrologer's own app has polled recently — see
    # _maybe_auto_close_stale.
    return _maybe_auto_close_stale(db, ticket)


def get_ticket_for_astrologer(db: Session, ticket_id: int, astrologer_id: int) -> Ticket:
    ticket = get_ticket(db, ticket_id)
    if ticket.astrologer_id != astrologer_id:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    return ticket


def list_tickets_for_astrologer(db: Session, astrologer_id: int) -> list[Ticket]:
    stmt = (
        select(Ticket)
        .where(Ticket.astrologer_id == astrologer_id)
        .order_by(Ticket.created_at.desc())
    )
    tickets = list(db.scalars(stmt).all())
    return [_maybe_auto_close_stale(db, t) for t in tickets]


def list_all_tickets(
    db: Session,
    *,
    status: TicketStatus | None = None,
    assigned_admin_id: int | None = None,
    sort: str = "desc",
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[Ticket]:
    """`assigned_admin_id` means "assigned to this admin" generically — it
    matches either the KAM (assigned_admin_id) or the language-matched CS
    (assigned_cs_id) column, so the same filter/dropdown works whichever role
    the picked admin has, and the ticket queue's "assigned to me" default
    (admin-app's TicketQueuePage) works for CS admins too.

    Gated by kam_notified/cs_notified: a KAM's regular astrologer filing a
    routine low-priority ticket they were never actually looped in on
    shouldn't clutter their queue just because they're that astrologer's
    personal contact — only tickets they were actually routed/notified for
    match (see create_ticket).

    `sort`: "desc"/"asc" order by creation time as before; "priority" orders
    by the astrologer's current queue priority (lower number = more urgent
    first — same source get_priority_ranking/create_ticket's VIP check use),
    ties broken by oldest first (so within a priority tier, whoever's been
    waiting longest surfaces first). Priority isn't a DB column (an
    astrologer's priority can change independently of any ticket), so this
    is a Python sort after fetching rather than a SQL ORDER BY — relies on
    Python's sort being stable, so tickets must be fetched oldest-first
    before the priority sort is applied.

    `date_from`/`date_to` filter on Ticket.created_at (when it was raised,
    not when it was resolved) — both inclusive, either can be given alone
    for an open-ended range, and equal values mean "just this one day".
    """
    stmt = select(Ticket)
    if status is not None:
        stmt = stmt.where(Ticket.status == status)
    if assigned_admin_id is not None:
        stmt = stmt.where(
            or_(
                and_(Ticket.assigned_admin_id == assigned_admin_id, Ticket.kam_notified.is_(True)),
                and_(Ticket.assigned_cs_id == assigned_admin_id, Ticket.cs_notified.is_(True)),
            )
        )
    if date_from is not None:
        stmt = stmt.where(Ticket.created_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        # Exclusive upper bound at the START of the next day, so the whole
        # end date is included regardless of the time-of-day component.
        stmt = stmt.where(Ticket.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    if sort == "priority":
        stmt = stmt.order_by(Ticket.created_at.asc())
        tickets = list(db.scalars(stmt).all())
        tickets.sort(key=lambda t: queue_performance_client.priority_sort_key(db, t.astrologer_id))
        return [_maybe_auto_close_stale(db, t) for t in tickets]

    stmt = stmt.order_by(Ticket.created_at.desc() if sort == "desc" else Ticket.created_at.asc())
    tickets = list(db.scalars(stmt).all())
    return [_maybe_auto_close_stale(db, t) for t in tickets]


def attach_astrologer_priority(db: Session, tickets: list[Ticket]) -> None:
    """Sets a transient `priority` attribute on each ticket's astrologer —
    not a DB column (priority can change independently of any ticket, same
    reasoning as the sort="priority" comment above), just enough for
    AstrologerRead.priority to pick up via from_attributes for the admin
    dashboard's ticket queue. Dedupes by astrologer_id so a queue page full
    of one astrologer's tickets doesn't refetch it once per row.
    """
    cache: dict[int, int] = {}
    for ticket in tickets:
        astrologer_id = ticket.astrologer_id
        if astrologer_id not in cache:
            cache[astrologer_id] = queue_performance_client.priority_sort_key(db, astrologer_id)
        ticket.astrologer.priority = cache[astrologer_id]
