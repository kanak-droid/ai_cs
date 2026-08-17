"""Owns every write to Ticket.status and TicketStatusHistory.

This is the ONLY module allowed to mutate ticket status. `_record_status`
inserts the history row and mirrors `ticket.status` in the same transaction,
so the two can never diverge — there is deliberately no other way to change a
ticket's status (no DB trigger, no ORM event hook; see the build plan for why).
"""

from datetime import timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.core.time import utcnow
from app.integrations import (
    admin_mapping_client,
    cs_assignment_client,
    queue_performance_client,
    slack_client,
)
from app.models.admin import Admin
from app.models.astrologer import Astrologer
from app.models.enums import TicketStatus
from app.models.ticket import Ticket
from app.models.ticket_status_history import TicketStatusHistory

# A resolved ticket the astrologer never responds to (satisfied/unsatisfied)
# auto-closes after this long — checked lazily on read, not via a background
# job, since nothing else in this app runs on a schedule.
_AUTO_CLOSE_AFTER = timedelta(days=5)

# Which team a ticket routes to for the Slack escalation notification — derived
# from category rather than a separate DB column, so this can change without a
# migration. Anything not explicitly a tech issue is treated as business.
_TECH_CATEGORIES = {"technical", "other"}
_TEAM_EMOJI = {"tech": "🛠️", "business": "💼"}

# Priority 1/2 astrologers ("P1"/"P2") get white-glove routing — their KAM is
# pulled in directly rather than just cc'd in the shared channel. Everyone
# else (P3+, or unknown/unlinked) goes through the standard CS flow. Uses the
# same queue_performance_client the get_priority_ranking tool uses (mock
# fallback included) so a ticket's routing never disagrees with whatever
# priority the model already told the astrologer in chat.
_VIP_PRIORITY_MAX = 2

# "No Visibility" routes straight to the KAM's own Slack channel instead of
# the shared CS one, but only for VIP (P1/P2) astrologers — P3+ goes through
# CS first (see prompt.py's "No Visibility" section).
_VIP_DIRECT_TO_KAM_CATEGORIES = {"no_visibility"}
# "Photo Change" (category "profile") always goes straight to the KAM,
# regardless of priority — the policy for this category carves out no P1/P2
# exception, unlike "no_visibility" above. CS isn't looped in at all for it.
_ALWAYS_DIRECT_TO_KAM_CATEGORIES = {"profile"}


def _team_for_category(category: str) -> str:
    return "tech" if category.strip().lower() in _TECH_CATEGORIES else "business"


def routing_for_ticket(category: str, is_vip: bool) -> tuple[bool, bool, bool]:
    """(direct_to_kam, kam_notified, cs_notified) for a ticket with this
    category/VIP-ness — the single source of truth create_ticket's Slack
    branch and scripts/backfill_ticket_notified.py both use, so the stored
    flags can never drift from the actual routing decision."""
    always_direct = category.strip().lower() in _ALWAYS_DIRECT_TO_KAM_CATEGORIES
    vip_direct = is_vip and category.strip().lower() in _VIP_DIRECT_TO_KAM_CATEGORIES
    direct_to_kam = always_direct or vip_direct
    return direct_to_kam, (direct_to_kam or is_vip), (not always_direct)


def is_vip_priority(db: Session, astrologer_id: int) -> bool:
    priority = queue_performance_client.get_queue_performance(db, astrologer_id).priority
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


def _record_status(
    db: Session, ticket: Ticket, status: TicketStatus, *, changed_by: str, note: str | None = None
) -> None:
    db.add(TicketStatusHistory(ticket_id=ticket.id, status=status, changed_by=changed_by, note=note))
    ticket.status = status
    if status == TicketStatus.RESOLVED:
        # Fresh resolution — start (or restart, after a reopen) the 5-day
        # satisfaction-response clock, and clear any satisfaction left over
        # from an earlier resolve/reopen cycle on this same ticket.
        ticket.resolved_at = utcnow()
        ticket.satisfaction = None


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
    is_vip = is_vip_priority(db, astrologer_id)
    normalized_category = category.strip().lower()

    direct_to_kam, kam_notified, cs_notified = routing_for_ticket(category, is_vip)
    always_direct = normalized_category in _ALWAYS_DIRECT_TO_KAM_CATEGORIES

    # Persisted so the dashboard's "assigned to me" filter can tell "this
    # admin was actually routed/notified" apart from "this is merely the
    # astrologer's regular KAM/language-matched CS" — see the Ticket model.
    ticket.kam_notified = kam_notified
    ticket.cs_notified = cs_notified

    priority = queue_performance_client.get_queue_performance(db, astrologer_id).priority
    priority_label = f"P{priority}" if priority is not None else "Unranked"
    expert_id_label = astrologer.expert_id if astrologer and astrologer.expert_id else "not linked"
    astrologer_name = astrologer.name if astrologer else "Unknown"

    header = f"{_TEAM_EMOJI.get(team, '🎫')} *New ticket #{ticket.id}*"
    body = (
        f"*Category:* {category} / {sub_category}\n"
        f"*Team:* {team} team\n"
        f"*Astrologer:* {astrologer_name} (#{astrologer_id}, expert_id: {expert_id_label}) — "
        f"Priority: {priority_label}"
    )
    cs_line = (
        f"\n*CS:* @{cs_name} ({'/'.join(cs_admin.languages) or 'no language set'})"
        if cs_name and ticket.cs_notified
        else ""
    )

    if direct_to_kam:
        # Routes straight to the KAM's own channel instead of the shared CS
        # one — "direct to KAM", not just cc'd.
        channel = admin.slack_channel if admin else settings.SLACK_SUPPORT_CHANNEL
        reason = "profile photo change" if always_direct else "priority astrologer"
        text = f"{header}\n{body}\n*Routed directly to you as their KAM ({reason}).*{cs_line}"
    elif is_vip:
        # VIP on any other category: shared channel, but KAM explicitly cc'd.
        channel = settings.SLACK_SUPPORT_CHANNEL
        text = f"{header}\n{body}\n*KAM:* @{kam_name} (priority astrologer — please loop in){cs_line}"
    else:
        # Standard CS routing — KAM stays the internal assignee but isn't
        # specially paged for a non-priority astrologer's ticket.
        channel = settings.SLACK_SUPPORT_CHANNEL
        text = f"{header}\n{body}{cs_line}"

    slack_client.post_message(db, channel=channel, text=text, ticket_id=ticket.id)
    if attachment_url:
        # Best-effort — pushes the actual photo/video into Slack (see
        # upload_attachment's docstring for why); never blocks ticket
        # creation if it fails.
        slack_client.upload_attachment(db, attachment_url=attachment_url, ticket_id=ticket.id)

    db.commit()
    db.refresh(ticket)
    return ticket


def transition_status(
    db: Session, ticket: Ticket, new_status: TicketStatus, *, changed_by: str, note: str | None = None
) -> Ticket:
    _record_status(db, ticket, new_status, changed_by=changed_by, note=note)
    db.commit()
    db.refresh(ticket)
    return ticket


def record_satisfaction(db: Session, ticket: Ticket, *, satisfied: bool) -> Ticket:
    """The astrologer's response to a resolved ticket, from the chat webview.

    Satisfied closes it out. Unsatisfied reopens it (back to under_review, so
    it lands in the KAM's queue again) rather than leaving it "resolved" when
    the astrologer says it isn't — the bot then asks what's still wrong.
    """
    if ticket.status != TicketStatus.RESOLVED:
        raise AppError("This ticket isn't awaiting a satisfaction response.")

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
            note="Auto-closed — no astrologer response after 5 days",
        )
        db.commit()
        db.refresh(ticket)
    return ticket


def get_ticket(db: Session, ticket_id: int) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    return ticket


def get_ticket_for_astrologer(db: Session, ticket_id: int, astrologer_id: int) -> Ticket:
    ticket = get_ticket(db, ticket_id)
    if ticket.astrologer_id != astrologer_id:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    return _maybe_auto_close_stale(db, ticket)


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
    ties broken by newest first. Priority isn't a DB column (an astrologer's
    priority can change independently of any ticket), so this is a Python
    sort after fetching rather than a SQL ORDER BY.
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

    if sort == "priority":
        stmt = stmt.order_by(Ticket.created_at.desc())
        tickets = list(db.scalars(stmt).all())
        tickets.sort(key=lambda t: _priority_for_sort(db, t.astrologer_id))
        return tickets

    stmt = stmt.order_by(Ticket.created_at.desc() if sort == "desc" else Ticket.created_at.asc())
    return list(db.scalars(stmt).all())


_UNRANKED_SORT_VALUE = 999


def _priority_for_sort(db: Session, astrologer_id: int) -> int:
    priority = queue_performance_client.get_queue_performance(db, astrologer_id).priority
    # Unranked sorts after every real P1-P5 ticket, not before (None can't
    # be compared to an int).
    return priority if priority is not None else _UNRANKED_SORT_VALUE


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
            cache[astrologer_id] = _priority_for_sort(db, astrologer_id)
        ticket.astrologer.priority = cache[astrologer_id]
