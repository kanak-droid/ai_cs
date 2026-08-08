from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_astrologer, get_db
from app.core.security import AstrologerContext
from app.schemas.chat import ChatRequest, ChatResponse, ChatTraceStep
from app.services import chat_service

router = APIRouter(tags=["chat"])


@router.post("/api/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    astrologer: AstrologerContext = Depends(get_current_astrologer),
    db: Session = Depends(get_db),
) -> ChatResponse:
    result = chat_service.handle_chat_turn(db, astrologer, body.message)
    return ChatResponse(
        reply=result.reply,
        trace=[ChatTraceStep(tool=s.tool, ok=s.ok, summary=s.summary) for s in result.trace],
    )
