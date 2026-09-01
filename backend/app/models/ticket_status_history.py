from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base
from app.models.enums import TicketStatus

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class TicketStatusHistory(Base):
    __tablename__ = "ticket_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", native_enum=False),
    )
    changed_at: Mapped[datetime] = mapped_column(default=utcnow)
    changed_by: Mapped[str] = mapped_column(String(120), default="system")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # True for a real status transition (_record_status); False for an
    # ownership/escalation log entry (_log_note) that reuses the ticket's
    # CURRENT status verbatim rather than actually changing it. Lets
    # chat-app's ticket-watcher tell the two apart — an escalation note is
    # written for the KAM, not the astrologer, and must never be announced
    # as if it were a status update.
    is_status_change: Mapped[bool] = mapped_column(default=True)

    ticket: Mapped["Ticket"] = relationship(back_populates="history")
