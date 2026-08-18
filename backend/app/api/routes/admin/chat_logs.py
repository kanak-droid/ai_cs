from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.schemas.chat_log import ChatSessionDetailRead, ChatSessionSummaryRead
from app.services import chat_log_service

router = APIRouter(tags=["admin"])


@router.get("/api/admin/chat-sessions", response_model=list[ChatSessionSummaryRead])
def list_chat_sessions(
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[ChatSessionSummaryRead]:
    sessions = chat_log_service.list_chat_sessions(db)
    return [ChatSessionSummaryRead.model_validate(s) for s in sessions]


@router.get("/api/admin/chat-sessions/{chat_session_id}", response_model=ChatSessionDetailRead)
def get_chat_session(
    chat_session_id: int,
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ChatSessionDetailRead:
    session = chat_log_service.get_chat_session(db, chat_session_id)
    return ChatSessionDetailRead.model_validate(session)
