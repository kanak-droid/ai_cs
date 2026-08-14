from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base
from app.models.enums import SessionResolution

if TYPE_CHECKING:
    from app.models.astrologer import Astrologer
    from app.models.ticket import Ticket


class ChatSession(Base):
    """One webview visit's worth of conversation, for analytics.

    Client-generated (chat-app mints a UUID on mount and sends it as
    `session_id` with every /api/chat call) rather than server-issued, since
    the backend itself is stateless — see chat_service.get_or_create_session.
    Not a source of truth for anything the astrologer/admin flows depend on;
    tickets and their status remain fully independent of this.
    """

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    astrologer_id: Mapped[int] = mapped_column(ForeignKey("astrologers.id"), index=True)

    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sub_category: Mapped[str | None] = mapped_column(String(80), nullable=True)

    resolved_by: Mapped[SessionResolution | None] = mapped_column(
        Enum(SessionResolution, name="session_resolution", native_enum=False), nullable=True
    )
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)

    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    astrologer: Mapped["Astrologer"] = relationship()
    ticket: Mapped["Ticket | None"] = relationship()
