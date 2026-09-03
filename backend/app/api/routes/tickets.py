from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_astrologer, get_db
from app.core.security import AstrologerContext
from app.schemas.ticket import TicketRatingRequest, TicketRead
from app.schemas.voice import CallRead
from app.services import call_service, ticket_service

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


@router.get("/api/tickets/{ticket_id}/follow-up-calls", response_model=list[CallRead])
def list_my_ticket_followup_calls(
    ticket_id: int,
    astrologer: AstrologerContext = Depends(get_current_astrologer),
    db: Session = Depends(get_db),
) -> list[CallRead]:
    """Shows the authenticated astrologer calls made about their own ticket."""
    ticket_service.get_ticket_for_astrologer(db, ticket_id, astrologer.astrologer_id)
    return [
        CallRead.model_validate(call)
        for call in call_service.list_calls_for_ticket(db, ticket_id=ticket_id)
    ]


@router.post("/api/tickets/{ticket_id}/rating", response_model=TicketRead)
def submit_ticket_rating(
    ticket_id: int,
    body: TicketRatingRequest,
    astrologer: AstrologerContext = Depends(get_current_astrologer),
    db: Session = Depends(get_db),
) -> TicketRead:
    ticket = ticket_service.get_ticket_for_astrologer(db, ticket_id, astrologer.astrologer_id)
    ticket = ticket_service.record_ticket_rating(
        db, ticket, rating=body.rating, reasons=body.reasons, comment=body.comment
    )
    return TicketRead.model_validate(ticket)
