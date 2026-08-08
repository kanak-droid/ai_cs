from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base
from app.models.enums import TicketStatus

if TYPE_CHECKING:
    from app.models.admin import Admin
    from app.models.astrologer import Astrologer
    from app.models.ticket_status_history import TicketStatusHistory


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    astrologer_id: Mapped[int] = mapped_column(ForeignKey("astrologers.id"), index=True)

    category: Mapped[str] = mapped_column(String(80))
    sub_category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    description_en: Mapped[str] = mapped_column(Text)
    preferred_language: Mapped[str] = mapped_column(String(40))
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    assigned_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id"), nullable=True)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", native_enum=False),
        default=TicketStatus.SUBMITTED,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    astrologer: Mapped["Astrologer"] = relationship()
    assigned_admin: Mapped["Admin | None"] = relationship()
    history: Mapped[list["TicketStatusHistory"]] = relationship(
        back_populates="ticket",
        order_by="TicketStatusHistory.changed_at",
        cascade="all, delete-orphan",
    )
