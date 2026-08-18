"""One row per turn (astrologer message or assistant reply) in a chat
session — see app/models/chat_session.py. Added 2026-08-18 for the admin
dashboard's chat-log view; before this, the backend never persisted
transcript text at all (only ChatSession's resolution metadata), so
conversations that happened before this shipped have no message rows,
only their ChatSession summary.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "astrologer" | "assistant"
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
