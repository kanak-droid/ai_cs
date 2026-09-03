from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
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

    # Vapi's own call id, returned synchronously from the create-call request
    # (see voice_client.create_call) — the only reliable key for matching a
    # later webhook back to this row. We deliberately do NOT rely on Vapi
    # echoing back custom metadata we set at creation time (its exact
    # passthrough field wasn't confirmed against a live Vapi payload as of
    # 2026-09-03) — every webhook Vapi sends carries the call's own id, so
    # looking that up against this column sidesteps the guess entirely.
    vapi_call_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)

    phone_number: Mapped[str] = mapped_column(String(20))
    # The chat-app ChatSession this call was requested from, if any (same
    # client-generated id as ChatRequest.session_id) — lets
    # call_service.handle_custom_llm_turn seed the very first model turn
    # with what the astrologer already told the text bot (via
    # chat_session_service.get_transcript_text), so the AI agent doesn't
    # make them repeat their issue. Nullable: nothing stops a call being
    # requested with no prior chat-app session at all.
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

    # Set if the AI agent called create_support_ticket mid-call (same tool,
    # same executor path as chat — see app/agent/tool_registry.py) so the
    # admin dashboard can link a call to the ticket it produced.
    created_ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    astrologer: Mapped["Astrologer"] = relationship()
    created_ticket: Mapped["Ticket | None"] = relationship()
