from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.models.enums import TicketStatus
from app.schemas.admin import AdminTicketRead
from app.schemas.ticket import TicketStatusUpdateRequest
from app.services import ticket_service

router = APIRouter(tags=["admin"])


@router.get("/api/admin/tickets", response_model=list[AdminTicketRead])
def list_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    assigned_admin_id: int | None = Query(default=None),
    sort: Literal["asc", "desc"] = Query(default="desc"),
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AdminTicketRead]:
    tickets = ticket_service.list_all_tickets(
        db,
        status=status_filter,
        assigned_admin_id=assigned_admin_id,
        sort_desc=(sort == "desc"),
    )
    return [AdminTicketRead.model_validate(t) for t in tickets]


@router.get("/api/admin/tickets/{ticket_id}", response_model=AdminTicketRead)
def get_ticket(
    ticket_id: int,
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminTicketRead:
    ticket = ticket_service.get_ticket(db, ticket_id)
    return AdminTicketRead.model_validate(ticket)


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
    return AdminTicketRead.model_validate(ticket)
