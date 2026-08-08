from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_astrologer, get_db
from app.core.security import AstrologerContext
from app.schemas.ticket import TicketRead
from app.services import ticket_service

router = APIRouter(tags=["tickets"])


@router.get("/api/tickets", response_model=list[TicketRead])
def list_my_tickets(
    astrologer: AstrologerContext = Depends(get_current_astrologer),
    db: Session = Depends(get_db),
) -> list[TicketRead]:
    tickets = ticket_service.list_tickets_for_astrologer(db, astrologer.astrologer_id)
    return [TicketRead.model_validate(t) for t in tickets]


@router.get("/api/tickets/{ticket_id}", response_model=TicketRead)
def get_my_ticket(
    ticket_id: int,
    astrologer: AstrologerContext = Depends(get_current_astrologer),
    db: Session = Depends(get_db),
) -> TicketRead:
    ticket = ticket_service.get_ticket_for_astrologer(db, ticket_id, astrologer.astrologer_id)
    return TicketRead.model_validate(ticket)
