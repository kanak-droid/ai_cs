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

    ticket: Mapped["Ticket"] = relationship(back_populates="history")
