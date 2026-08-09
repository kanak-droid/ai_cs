"""Maps tool names to handlers. Only agent/executor.py resolves a handler here —
the orchestrator only ever sees agent/tool_schemas.py (pure data).

Each handler receives `(tool_input, ctx)` where `tool_input["astrologer_id"]` has
already been overwritten by the executor with `ctx.astrologer_id` — handlers must
use `ctx.astrologer_id`, never read astrologer_id out of tool_input.
"""

from dataclasses import dataclass
from typing import Callable

from app.agent.context import SessionContext
from app.integrations import (
    admin_mapping_client,
    kyc_client,
    n8n_client,
    payout_client,
    salary_client,
)
from app.schemas.ticket import TicketRead
from app.services import ticket_service


@dataclass(frozen=True)
class ToolResult:
    content_for_model: str
    summary_for_trace: str
    is_error: bool = False


@dataclass(frozen=True)
class ToolSpec:
    name: str
    handler: Callable[[dict, SessionContext], ToolResult]


def _handle_get_payout_status(tool_input: dict, ctx: SessionContext) -> ToolResult:
    result = payout_client.get_payout_status(ctx.astrologer_id)
    return ToolResult(
        content_for_model=(
            f"status={result.status} amount_inr={result.amount_inr} "
            f"scheduled_date={result.scheduled_date} last_paid_date={result.last_paid_date}"
        ),
        summary_for_trace="Checked your payout status",
    )


def _handle_get_kyc_status(tool_input: dict, ctx: SessionContext) -> ToolResult:
    result = kyc_client.get_kyc_status(ctx.astrologer_id)
    content = f"status={result.status}"
    if result.reason:
        content += f" reason={result.reason}"
    return ToolResult(content_for_model=content, summary_for_trace="Checked your KYC status")


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
    return ToolResult(
        content_for_model=f"assigned_admin_id={result.admin_id}",
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
    result = n8n_client.trigger_photo_beautify(ctx.astrologer_id, image_url)
    return ToolResult(
        content_for_model=f"processed_image_url={result.processed_image_url}",
        summary_for_trace="Ran your photo through the beautify pipeline",
    )


def _handle_create_support_ticket(tool_input: dict, ctx: SessionContext) -> ToolResult:
    ticket = ticket_service.create_ticket(
        ctx.db,
        astrologer_id=ctx.astrologer_id,
        category=tool_input.get("category", "other"),
        sub_category=tool_input.get("sub_category", "general"),
        description=tool_input.get("description", ""),
        description_en=tool_input.get("description_en", ""),
        preferred_language=ctx.language,
        attachment_url=tool_input.get("attachment_url"),
    )
    ticket_read = TicketRead.model_validate(ticket)
    return ToolResult(
        content_for_model=ticket_read.model_dump_json(),
        summary_for_trace=f"Created ticket #{ticket.id} for you",
    )


def _handle_get_tickets(tool_input: dict, ctx: SessionContext) -> ToolResult:
    tickets = ticket_service.list_tickets_for_astrologer(ctx.db, ctx.astrologer_id)
    tickets_read = [TicketRead.model_validate(t).model_dump() for t in tickets]
    return ToolResult(
        content_for_model=str(tickets_read),
        summary_for_trace="Looked up your tickets",
    )


REGISTRY: dict[str, ToolSpec] = {
    spec.name: spec
    for spec in [
        ToolSpec("get_payout_status", _handle_get_payout_status),
        ToolSpec("get_kyc_status", _handle_get_kyc_status),
        ToolSpec("get_salary_details", _handle_get_salary_details),
        ToolSpec("get_assigned_admin", _handle_get_assigned_admin),
        ToolSpec("trigger_photo_beautify", _handle_trigger_photo_beautify),
        ToolSpec("create_support_ticket", _handle_create_support_ticket),
        ToolSpec("get_tickets", _handle_get_tickets),
    ]
}
