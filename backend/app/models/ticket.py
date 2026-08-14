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

    # The astrologer's personal KAM (priority-based routing) — see
    # admin_mapping_client.
    assigned_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id"), nullable=True)
    # The CS handling this ticket day-to-day, round-robin'd by the
    # astrologer's language — see cs_assignment_client. Independent of
    # assigned_admin_id: a VIP ticket still gets a language-matched CS even
    # though its KAM is also pulled in for escalation.
    assigned_cs_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id"), nullable=True)
    # Whether the KAM/CS above was actually routed/notified for this specific
    # ticket (mirrors the Slack routing decision made at creation — see
    # ticket_service.create_ticket) — NOT just "is this the astrologer's
    # regular contact/language match". A ticket queue filtered to a given
    # admin only shows tickets where that flag is true for them, so a KAM
    # isn't shown every low-priority ticket their astrologers ever file, only
    # the ones they were actually looped in on.
    kam_notified: Mapped[bool] = mapped_column(default=True)
    cs_notified: Mapped[bool] = mapped_column(default=True)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", native_enum=False),
        default=TicketStatus.SUBMITTED,
        index=True,
    )
    # Set whenever status transitions to RESOLVED (cleared back to None on the
    # same transition, so a later reopen-and-reresolve cycle awaits a fresh
    # response) — drives the astrologer-facing satisfaction prompt and the
    # 5-day auto-close check. See ticket_service._record_status.
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # "satisfied" | "unsatisfied" | None — the astrologer's response to the
    # most recent resolution. Only ticket_service.record_satisfaction writes this.
    satisfaction: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    astrologer: Mapped["Astrologer"] = relationship()
    assigned_admin: Mapped["Admin | None"] = relationship(foreign_keys="Ticket.assigned_admin_id")
    assigned_cs: Mapped["Admin | None"] = relationship(foreign_keys="Ticket.assigned_cs_id")
    history: Mapped[list["TicketStatusHistory"]] = relationship(
        back_populates="ticket",
        order_by="TicketStatusHistory.changed_at",
        cascade="all, delete-orphan",
    )
