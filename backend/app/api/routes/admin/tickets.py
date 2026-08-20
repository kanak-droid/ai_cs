from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db, require_admin_access
from app.core.security import AdminContext
from app.integrations import object_storage
from app.models.enums import TicketStatus
from app.schemas.admin import AdminTicketRead
from app.schemas.ticket import (
    AttachmentPreviewResponse,
    TicketEscalateRequest,
    TicketReassignRequest,
    TicketStatusUpdateRequest,
)
from app.services import ticket_service

router = APIRouter(tags=["admin"])


@router.get("/api/admin/tickets", response_model=list[AdminTicketRead])
def list_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    assigned_admin_id: int | None = Query(default=None),
    sort: Literal["asc", "desc", "priority"] = Query(default="desc"),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AdminTicketRead]:
    tickets = ticket_service.list_all_tickets(
        db,
        status=status_filter,
        assigned_admin_id=assigned_admin_id,
        sort=sort,
        date_from=date_from,
        date_to=date_to,
    )
    ticket_service.attach_astrologer_priority(db, tickets)
    return [AdminTicketRead.model_validate(t) for t in tickets]


@router.get("/api/admin/tickets/{ticket_id}", response_model=AdminTicketRead)
def get_ticket(
    ticket_id: int,
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminTicketRead:
    ticket = ticket_service.get_ticket(db, ticket_id)
    ticket_service.attach_astrologer_priority(db, [ticket])
    return AdminTicketRead.model_validate(ticket)


@router.get("/api/admin/tickets/{ticket_id}/attachment", response_model=AttachmentPreviewResponse)
def get_ticket_attachment_preview_url(
    ticket_id: int,
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AttachmentPreviewResponse:
    """Returns a short-lived, signed URL for the ticket's attachment instead
    of its raw S3 URL — the browser has no AWS credentials, so an <img src>
    pointed straight at the real URL 403s unless the bucket has a
    public-read policy attached. The signed URL works regardless (signed
    with our own credentials/IAM role) and the browser can load it directly
    — no proxying file bytes through our own server at all. Requires the
    admin JWT like any other admin route, so a signed link is only ever
    handed to a logged-in admin, even though the link itself doesn't
    require auth once issued.
    """
    ticket = ticket_service.get_ticket(db, ticket_id)
    if not ticket.attachment_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No attachment on this ticket")
    return AttachmentPreviewResponse(preview_url=object_storage.generate_preview_url(ticket.attachment_url))


@router.patch("/api/admin/tickets/{ticket_id}", response_model=AdminTicketRead)
def update_ticket_status(
    ticket_id: int,
    body: TicketStatusUpdateRequest,
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminTicketRead:
    ticket = ticket_service.get_ticket(db, ticket_id)
    ticket = ticket_service.transition_status(
        db, ticket, body.status, changed_by=admin.email, note=body.note
    )
    ticket_service.attach_astrologer_priority(db, [ticket])
    return AdminTicketRead.model_validate(ticket)


@router.post("/api/admin/tickets/{ticket_id}/escalate", response_model=AdminTicketRead)
def escalate_ticket_to_kam(
    ticket_id: int,
    body: TicketEscalateRequest,
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminTicketRead:
    ticket = ticket_service.get_ticket(db, ticket_id)
    ticket = ticket_service.escalate_to_kam(db, ticket, changed_by=admin.email, note=body.note)
    ticket_service.attach_astrologer_priority(db, [ticket])
    return AdminTicketRead.model_validate(ticket)


@router.post("/api/admin/tickets/{ticket_id}/reassign", response_model=AdminTicketRead)
def reassign_ticket(
    ticket_id: int,
    body: TicketReassignRequest,
    # Reassigning ownership is an ADMIN-access-level action, same tier as
    # granting/editing another admin's access — a normal-access KAM/CS
    # shouldn't be able to move a ticket off of someone else.
    admin: AdminContext = Depends(require_admin_access),
    db: Session = Depends(get_db),
) -> AdminTicketRead:
    ticket = ticket_service.get_ticket(db, ticket_id)
    ticket = ticket_service.reassign_ticket(
        db,
        ticket,
        role=body.role,
        new_admin_id=body.admin_id,
        changed_by=admin.email,
        note=body.note,
    )
    ticket_service.attach_astrologer_priority(db, [ticket])
    return AdminTicketRead.model_validate(ticket)
