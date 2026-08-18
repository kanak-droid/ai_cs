from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import SessionResolution


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    text: str
    created_at: datetime


class ChatSessionSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    astrologer_id: int
    # Transient — set by chat_log_service, not real columns on ChatSession
    # (same convention as AstrologerRead.priority; see ticket_service).
    astrologer_name: str
    priority: int | None = None
    category: str | None = None
    sub_category: str | None = None
    resolved_by: SessionResolution | None = None
    ticket_id: int | None = None
    started_at: datetime
    resolved_at: datetime | None = None


class ChatSessionDetailRead(ChatSessionSummaryRead):
    messages: list[ChatMessageRead] = []
