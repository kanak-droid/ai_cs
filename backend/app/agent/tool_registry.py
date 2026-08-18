"""Maps tool names to handlers. Only agent/executor.py resolves a handler here —
the orchestrator only ever sees agent/tool_schemas.py (pure data).

Each handler receives `(tool_input, ctx)` where `tool_input["astrologer_id"]` has
already been overwritten by the executor with `ctx.astrologer_id` — handlers must
use `ctx.astrologer_id`, never read astrologer_id out of tool_input.
"""

from dataclasses import dataclass, field
from typing import Callable

from app.agent import vision
from app.agent.context import SessionContext
from app.integrations import (
    admin_mapping_client,
    kyc_client,
    n8n_client,
    payout_client,
    queue_performance_client,
    salary_client,
)
from app.models.admin import Admin
from app.schemas.ticket import TicketRead
from app.services import chat_session_service, ticket_service


@dataclass(frozen=True)
class ToolResult:
    content_for_model: str
    summary_for_trace: str
    is_error: bool = False
    # Out-of-band data the API layer surfaces to the frontend (e.g. a newly
    # created ticket's id, or a flag to show the feedback widget) — never
    # seen by the model itself, only read by chat_service/routes.
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    handler: Callable[[dict, SessionContext], ToolResult]


def _handle_get_payout_status(tool_input: dict, ctx: SessionContext) -> ToolResult:
    result = payout_client.get_payout_status(ctx.db, ctx.astrologer_id)
    content = (
        f"status={result.status} amount_inr={result.amount_inr} "
        f"scheduled_date={result.scheduled_date} last_paid_date={result.last_paid_date}"
    )
    if result.wallet_balance_inr is not None:
        content += f" wallet_balance_inr={result.wallet_balance_inr}"
    # TDS is the most common reason a payout looks lower than expected —
    # incomplete KYC means a much higher rate. Only present when this
    # astrologer has a real linked payout row (see payout_client.py).
    if result.tds_deducted_percent is not None:
        # Only present for a real linked payout row — also the signal that
        # scheduled_date above came from the real, sheet-derived cadence
        # below, not the unrelated mocked fallback pattern (which has
        # nothing to do with alternate Fridays at all).
        content += (
            f" this_cycle_kyc_status={result.kyc_status} "
            f"tds_deducted_percent={result.tds_deducted_percent} "
            f"tds_amount_inr={result.tds_amount_inr} "
            f"payout_cadence=\"runs every alternate Friday\""
        )
    return ToolResult(content_for_model=content, summary_for_trace="Checked your payout status")


def _handle_get_kyc_status(tool_input: dict, ctx: SessionContext) -> ToolResult:
    result = kyc_client.get_kyc_status(ctx.db, ctx.astrologer_id)
    content = f"status={result.status}"
    if result.reason:
        content += f" reason={result.reason}"
    return ToolResult(content_for_model=content, summary_for_trace="Checked your KYC status")


def _handle_get_priority_ranking(tool_input: dict, ctx: SessionContext) -> ToolResult:
    result = queue_performance_client.get_queue_performance(ctx.db, ctx.astrologer_id)
    priority_str = (
        str(result.priority)
        if result.priority is not None
        else "not yet ranked (not enough recent activity/bookings to rank yet)"
    )
    return ToolResult(
        content_for_model=(
            f"priority={priority_str} users_connected={result.users_connected} "
            f"queues_connected={result.queues_connected} "
            f"total_talktime_min={result.total_talktime_min}"
        ),
        summary_for_trace="Checked your priority ranking",
    )


def _handle_get_salary_details(tool_input: dict, ctx: SessionContext) -> ToolResult:
    result = salary_client.get_salary_details(ctx.astrologer_id)
    return ToolResult(
        content_for_model=(
            f"monthly_salary_inr={result.monthly_salary_inr} "
            f"last_revision_date={result.last_revision_date} next_review_date={result.next_review_date}"
        ),
        summary_for_trace="Checked your salary details",
    )


def _handle_get_assigned_admin(tool_input: dict, ctx: SessionContext) -> ToolResult:
    result = admin_mapping_client.get_assigned_admin(ctx.db, ctx.astrologer_id)
    admin = ctx.db.get(Admin, result.admin_id)
    return ToolResult(
        content_for_model=f"assigned_admin_name={admin.name if admin else None}",
        summary_for_trace="Looked up your assigned support contact",
    )


def _handle_trigger_photo_beautify(tool_input: dict, ctx: SessionContext) -> ToolResult:
    image_url = tool_input.get("image_url")
    if not image_url:
        return ToolResult(
            content_for_model="error: image_url is required",
            summary_for_trace="Photo beautify failed — no image provided",
            is_error=True,
        )
    try:
        result = n8n_client.trigger_photo_beautify(ctx.db, ctx.astrologer_id, image_url)
    except Exception:
        # Real n8n path only (network error, or the poll timed out with no
        # result logged) — never silently claim a beautified image exists.
        return ToolResult(
            content_for_model=(
                "error: the photo enhancement service didn't return a result in time — "
                "tell the astrologer to try again in a bit, don't claim it succeeded."
            ),
            summary_for_trace="Photo beautify didn't complete in time",
            is_error=True,
        )
    return ToolResult(
        content_for_model=f"processed_image_url={result.processed_image_url}",
        summary_for_trace="Ran your photo through the beautify pipeline",
    )


def _handle_analyze_screenshot(tool_input: dict, ctx: SessionContext) -> ToolResult:
    image_url = tool_input.get("image_url") or ctx.last_attachment_url
    question = tool_input.get("question") or "What issue or error is visible in this image?"
    if not image_url:
        return ToolResult(
            content_for_model="error: image_url is required",
            summary_for_trace="Couldn't analyze — no image shared yet",
            is_error=True,
        )
    try:
        diagnosis = vision.analyze_image(image_url, question)
    except Exception:
        return ToolResult(
            content_for_model="error: could not analyze the image",
            summary_for_trace="Couldn't analyze your screenshot",
            is_error=True,
        )
    return ToolResult(content_for_model=diagnosis, summary_for_trace="Looked at your screenshot")


def _handle_create_support_ticket(tool_input: dict, ctx: SessionContext) -> ToolResult:
    category = tool_input.get("category", "other")
    attachment_url = tool_input.get("attachment_url") or ctx.last_attachment_url

    # Code-enforced (2026-08-16): never raise a second ticket for the same
    # problem while an earlier one for this category is still open — checked
    # first, before evidence, since there's no point asking for a fresh
    # photo/video for a duplicate that shouldn't be created at all.
    existing = ticket_service.get_active_ticket_for_category(ctx.db, ctx.astrologer_id, category)
    if existing is not None:
        return ToolResult(
            content_for_model=(
                f"error: astrologer already has an active ticket for this — ticket "
                f"#{existing.id}, status '{existing.status.value}'. Do NOT create another "
                "one. Tell them this issue is already in the queue and being worked on, "
                'and ask them to check the "My Tickets" section (bottom right) to see its '
                "current priority/status."
            ),
            summary_for_trace="Already has an active ticket for this — didn't raise a duplicate",
            is_error=True,
        )

    if ticket_service.needs_evidence(category) and not attachment_url:
        return ToolResult(
            content_for_model=(
                "error: a photo or video of the issue is required before raising this "
                "ticket — ask the astrologer to share one first, then call this again."
            ),
            summary_for_trace="Needs a photo/video before this ticket can be raised",
            is_error=True,
        )

    # Code-enforced, not just a prompt instruction (2026-08-16): a non-VIP
    # "no_visibility" complaint should get self-help advice first, not an
    # immediate ticket — the prompt says so, but the model doesn't reliably
    # follow that instruction every time (observed live — see
    # docs/chatbot-approach.md §7d). has_prior_reply is a mechanical fact
    # about the conversation's shape (has this astrologer already had one
    # round-trip in this chat?), not something the model can talk its way
    # around — so the very first message about low calls can't skip
    # straight to a ticket for a non-VIP astrologer, no matter what the
    # model decides.
    if (
        category.strip().lower() == "no_visibility"
        and not ctx.has_prior_reply
        and not ticket_service.is_vip_priority(ctx.db, ctx.astrologer_id)
    ):
        return ToolResult(
            content_for_model=(
                "error: don't raise this ticket yet. This astrologer isn't VIP priority, "
                "and this is their first message about it — give them the self-help "
                "advice from the prompt first (availability especially at peak hours, "
                "encouraging regular customers to call more, keeping calls engaged "
                "longer) and explain how priority works, instead of calling this tool. "
                "Only call it again if they come back still unsatisfied after that."
            ),
            summary_for_trace="Give self-help advice before raising this ticket",
            is_error=True,
        )

    ticket = ticket_service.create_ticket(
        ctx.db,
        astrologer_id=ctx.astrologer_id,
        category=category,
        sub_category=tool_input.get("sub_category", "general"),
        description=tool_input.get("description", ""),
        description_en=tool_input.get("description_en", ""),
        preferred_language=ctx.language,
        attachment_url=attachment_url,
    )
    chat_session_service.mark_escalated(ctx.db, ctx.session_id, ticket_id=ticket.id)
    ticket_read = TicketRead.model_validate(ticket)

    # Real name of whoever was ACTUALLY notified (kam_notified/cs_notified —
    # see ticket_service.create_ticket), not just whoever is nominally
    # assigned — a standard non-VIP ticket still has a personal KAM on
    # assigned_admin_id even though they weren't specially paged for it, so
    # naming them here would overclaim who's actually looking at this. None
    # means "don't name anyone" — never let the model invent a name.
    notified_kam_name = None
    if ticket.kam_notified and ticket.assigned_admin_id:
        kam = ctx.db.get(Admin, ticket.assigned_admin_id)
        notified_kam_name = kam.name if kam else None
    notified_cs_name = None
    if ticket.cs_notified and ticket.assigned_cs_id:
        cs = ctx.db.get(Admin, ticket.assigned_cs_id)
        notified_cs_name = cs.name if cs else None

    return ToolResult(
        content_for_model=(
            f"{ticket_read.model_dump_json()} "
            f"notified_kam_name={notified_kam_name} notified_cs_name={notified_cs_name}"
        ),
        summary_for_trace=f"Created ticket #{ticket.id} for you",
        # show_feedback closes out this chat thread client-side (see
        # ChatPage.tsx) the same way mark_issue_resolved does — raising a
        # ticket is a terminal action for THIS conversation too, not just a
        # resolved-without-a-ticket one.
        metadata={"created_ticket_id": ticket.id, "show_feedback": True},
    )


def _handle_get_tickets(tool_input: dict, ctx: SessionContext) -> ToolResult:
    tickets = ticket_service.list_tickets_for_astrologer(ctx.db, ctx.astrologer_id)
    tickets_read = [TicketRead.model_validate(t).model_dump() for t in tickets]
    return ToolResult(
        content_for_model=str(tickets_read),
        summary_for_trace="Looked up your tickets",
    )


def _handle_mark_issue_resolved(tool_input: dict, ctx: SessionContext) -> ToolResult:
    category = tool_input.get("category", "other")
    sub_category = tool_input.get("sub_category", "general")
    chat_session_service.mark_resolved_by_bot(
        ctx.db, ctx.session_id, category=category, sub_category=sub_category
    )
    return ToolResult(
        content_for_model="ok",
        summary_for_trace="Marked this issue as resolved",
        metadata={"show_feedback": True},
    )


REGISTRY: dict[str, ToolSpec] = {
    spec.name: spec
    for spec in [
        ToolSpec("get_payout_status", _handle_get_payout_status),
        ToolSpec("get_kyc_status", _handle_get_kyc_status),
        ToolSpec("get_priority_ranking", _handle_get_priority_ranking),
        ToolSpec("get_assigned_admin", _handle_get_assigned_admin),
        # get_salary_details and trigger_photo_beautify intentionally not
        # registered — see tool_schemas.py's ALL_TOOLS comment. Handlers
        # kept below, unused, so re-enabling either later is a one-line
        # change in both files.
        ToolSpec("analyze_screenshot", _handle_analyze_screenshot),
        ToolSpec("create_support_ticket", _handle_create_support_ticket),
        ToolSpec("get_tickets", _handle_get_tickets),
        ToolSpec("mark_issue_resolved", _handle_mark_issue_resolved),
    ]
}
