from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.integrations import queue_performance_client
from app.models.astrologer import Astrologer
from app.models.call import Call
from app.models.chat_session import ChatSession
from app.models.ticket import Ticket
from app.schemas.admin import AstrologerRead
from app.schemas.call_log import CallLogSummaryRead
from app.schemas.chat_log import ChatSessionSummaryRead
from app.schemas.ticket import TicketRead

router = APIRouter(tags=["admin"])


@router.get("/api/admin/astrologers", response_model=list[AstrologerRead])
def list_astrologers(
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AstrologerRead]:
    astrologers = db.scalars(select(Astrologer).order_by(Astrologer.name)).all()
    return [AstrologerRead.model_validate(a) for a in astrologers]


@router.get("/api/admin/astrologers/search")
def search_astrologers(
    q: str = Query(min_length=1),
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AstrologerRead]:
    term = q.strip()
    if term.isdigit():
        stmt = select(Astrologer).where(Astrologer.id == int(term))
    else:
        stmt = select(Astrologer).where(Astrologer.name.ilike(f"%{term}%"))
    stmt = stmt.order_by(Astrologer.name).limit(20)
    return [AstrologerRead.model_validate(a) for a in db.scalars(stmt).all()]


@router.get("/api/admin/astrologers/{astrologer_id}/overview")
def get_astrologer_overview(
    astrologer_id: int,
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    astrologer = db.get(Astrologer, astrologer_id)
    if astrologer is None:
        raise HTTPException(status_code=404, detail="Astrologer not found")

    priority = queue_performance_client.get_queue_performance(db, astrologer_id).priority
    astrologer.priority = priority  # type: ignore[attr-defined]

    tickets = list(
        db.scalars(
            select(Ticket)
            .where(Ticket.astrologer_id == astrologer_id)
            .order_by(Ticket.created_at.desc())
            .limit(50)
        )
    )

    calls_stmt = (
        select(Call)
        .where(Call.astrologer_id == astrologer_id)
        .options(joinedload(Call.astrologer))
        .order_by(Call.created_at.desc())
        .limit(50)
    )
    calls = list(db.scalars(calls_stmt).unique())
    for call in calls:
        call.astrologer_name = astrologer.name  # type: ignore[attr-defined]
        call.priority = priority  # type: ignore[attr-defined]

    chat_sessions = list(
        db.scalars(
            select(ChatSession)
            .where(ChatSession.astrologer_id == astrologer_id)
            .options(joinedload(ChatSession.astrologer))
            .order_by(ChatSession.started_at.desc())
            .limit(50)
        ).unique()
    )
    for session in chat_sessions:
        session.astrologer_name = astrologer.name  # type: ignore[attr-defined]
        session.priority = priority  # type: ignore[attr-defined]

    return {
        "astrologer": AstrologerRead.model_validate(astrologer),
        "tickets": [TicketRead.model_validate(t) for t in tickets],
        "calls": [CallLogSummaryRead.model_validate(c) for c in calls],
        "chat_sessions": [ChatSessionSummaryRead.model_validate(s) for s in chat_sessions],
    }
