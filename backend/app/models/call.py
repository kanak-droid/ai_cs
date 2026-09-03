from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base
from app.models.enums import CallStatus

if TYPE_CHECKING:
    from app.models.astrologer import Astrologer
    from app.models.ticket import Ticket


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    astrologer_id: Mapped[int] = mapped_column(ForeignKey("astrologers.id"), index=True)

    # Twilio's own CallSid, returned synchronously from the create-call
    # request (see voice_client.create_call) — passed back to us in both the
    # TwiML-fetch request and the status-callback webhook (as CallSid), and
    # again as `callSid` in the ConversationRelay WebSocket's setup message,
    # so this is the one column that ties all three back to the same row.
    twilio_call_sid: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )

    phone_number: Mapped[str] = mapped_column(String(20))
    # A call can start from an existing support ticket or directly from the
    # "request a call" control in chat. One Call table owns both flows.
    ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("tickets.id"), nullable=True, index=True
    )
    triggered_by: Mapped[str] = mapped_column(String(80), default="user_request")
    # Per-call opaque reference in every Twilio URL. Unlike an incrementing
    # id, this is safe to expose to Twilio and application logs.
    relay_token: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True, index=True
    )
    # The chat-app ChatSession this call was requested from, if any (same
    # client-generated id as ChatRequest.session_id) — lets the
    # ConversationRelay WebSocket handler (see app/api/routes/voice.py) seed
    # the very first model turn with what the astrologer already told the
    # text bot (via chat_session_service.get_transcript_text), so the AI
    # agent doesn't make them repeat their issue. Nullable: nothing stops a
    # call being requested with no prior chat-app session at all.
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus, name="call_status", native_enum=False),
        default=CallStatus.QUEUED,
        index=True,
    )
    ended_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Full transcript text, appended to as transcript webhook events arrive;
    # final copy also lands here from the end-of-call-report. Kept as one
    # blob (not a child table) since nothing queries individual lines yet —
    # same call as chat_session_service.record_message not needing a
    # separate table until the admin dashboard needs per-line filtering.
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Structured end-of-call outcome for the support dashboard. All fields
    # are nullable so historical calls remain readable after the migration.
    support_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    suggested_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    actions_taken: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    summary_generated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Set if the AI agent called create_support_ticket mid-call (same tool,
    # same executor path as chat — see app/agent/tool_registry.py) so the
    # admin dashboard can link a call to the ticket it produced.
    created_ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    astrologer: Mapped["Astrologer"] = relationship()
    created_ticket: Mapped["Ticket | None"] = relationship(foreign_keys=[created_ticket_id])
    ticket: Mapped["Ticket | None"] = relationship(foreign_keys=[ticket_id])
