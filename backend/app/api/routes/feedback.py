from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_astrologer, get_db
from app.core.errors import NotFoundError
from app.core.security import AstrologerContext
from app.schemas.chat import SessionFeedbackRequest
from app.services import chat_session_service

router = APIRouter(tags=["feedback"])


@router.post("/api/chat/sessions/{session_id}/feedback")
def submit_session_feedback(
    session_id: str,
    body: SessionFeedbackRequest,
    astrologer: AstrologerContext = Depends(get_current_astrologer),
    db: Session = Depends(get_db),
) -> dict:
    session = chat_session_service.record_feedback(
        db,
        session_id,
        astrologer.astrologer_id,
        rating=body.rating,
        reasons=body.reasons,
        comment=body.comment,
    )
    if session is None:
        raise NotFoundError("Chat session not found")
    return {"status": "ok"}
