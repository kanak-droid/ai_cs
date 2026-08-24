from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, String, Text
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
    # "satisfied" | "unsatisfied" | None — derived from `rating` below
    # (>=4 stars is "satisfied") by ticket_service.record_ticket_rating, the
    # only writer of any of these four rating fields. Kept as its own column
    # (rather than computed from rating on read) since it predates the star
    # rating and analytics already queries it directly.
    satisfaction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # The astrologer's 1-5 star rating of the most recent resolution, plus
    # why: `rating_reasons` is a list of preset reason strings (which ones
    # depend on whether rating was high or low — see chat-app's
    # TicketRatingWidget), `rating_comment` is optional free text. All four
    # cleared back to None by _record_status whenever the ticket transitions
    # to RESOLVED again (same reopen-and-reresolve reasoning as satisfaction
    # above), so a stale rating from a previous resolution cycle never lingers.
    rating: Mapped[int | None] = mapped_column(nullable=True)
    rating_reasons: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    rating_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    rated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Set by ticket_service.escalate_to_kam — a CS-initiated handoff to the
    # KAM, distinct from the routing decided at creation (kam_notified
    # above). Exists so analytics can exclude an escalated ticket from a
    # CS's "resolved" tally even though assigned_cs_id never changes (the CS
    # stays associated for reference; the KAM is who actually resolves it).
    escalated_to_kam: Mapped[bool] = mapped_column(default=False)
    escalated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Set once this ticket has been pushed into Zoho Desk (see
    # ticket_service._maybe_push_to_zoho) — only happens for cs_notified
    # tickets. None means either "never pushed" (e.g. a profile-category
    # ticket that's never been to a CS) or "push attempted but failed" —
    # there's no background retry; the only later chance to push is
    # reassign_ticket flipping cs_notified True for a ticket that started
    # without a CS.
    zoho_ticket_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

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
