from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.errors import ForbiddenError, NotFoundError
from app.models.enums import TicketStatus
from app.models.ticket import Ticket
from app.schemas.zoho import ZohoWebhookRequest
from app.services import ticket_service

router = APIRouter(tags=["integrations"])

_TERMINAL_STATUSES = (TicketStatus.RESOLVED, TicketStatus.CLOSED)


@router.post("/api/integrations/zoho/webhook")
def handle_zoho_webhook(
    body: ZohoWebhookRequest,
    db: Session = Depends(get_db),
    x_zoho_webhook_secret: str | None = Header(default=None),
) -> dict:
    """Pull side of the Zoho Desk two-way sync — a CS working a ticket from
    Zoho instead of our dashboard. Zoho can't present our astrologer/admin
    JWT, so auth here is a shared secret header instead (same static-
    credential convention as every other integration in this app, not an
    HMAC signature scheme).

    Every status change is routed through the real ticket_service
    functions (transition_status/escalate_to_kam), never a raw column
    write — so the existing invariants (a resolved ticket needs a note, it
    triggers the astrologer's rating flow, escalating notifies the KAM)
    still apply exactly the same as a change made from our own dashboard.
    Zoho's "Closed" maps to our `resolved`, never `closed` directly —
    `closed` is reserved for the astrologer's own confirmation or the 48h
    auto-close, both of which the rating flow depends on; skipping straight
    to it here would silently bypass that.
    """
    if not settings.ZOHO_WEBHOOK_SECRET or x_zoho_webhook_secret != settings.ZOHO_WEBHOOK_SECRET:
        raise ForbiddenError("Invalid or missing webhook secret")

    ticket = db.scalars(select(Ticket).where(Ticket.zoho_ticket_id == body.ticket_id)).first()
    if ticket is None:
        raise NotFoundError(f"No AstroHelp ticket linked to Zoho ticket {body.ticket_id}")

    # Idempotent against Zoho redelivering the same webhook — re-applying
    # an already-applied status would otherwise add a duplicate history row
    # (and, for "Closed", spuriously restart the rating-response clock).
    if body.status == "Closed":
        if ticket.status not in _TERMINAL_STATUSES:
            ticket_service.transition_status(
                db,
                ticket,
                TicketStatus.RESOLVED,
                changed_by="zoho",
                note=body.note or "Resolved via Zoho Desk",
            )
    elif body.status == "Escalated":
        if not ticket.escalated_to_kam:
            ticket_service.escalate_to_kam(
                db, ticket, changed_by="zoho", note=body.note or "Escalated via Zoho Desk"
            )
    # "Open" / "On Hold" (or anything unrecognized) — no-op.

    return {"status": "ok"}
