from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.enums import CallStatus


class RequestCallBody(BaseModel):
    # Same client-generated id as ChatRequest.session_id — lets the call
    # pick up context from whatever the astrologer already told the text
    # bot in this webview visit. Optional: the "Request a call" button can
    # be shown with no prior chat at all.
    session_id: str | None = None


class RequestCallResponse(BaseModel):
    call_id: int
    status: str


class CallRead(BaseModel):
    """A persisted phone-call lifecycle safe for its owner or support staff."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    astrologer_id: int
    ticket_id: int | None = None
    phone_number: str
    triggered_by: str
    status: CallStatus
    ended_reason: str | None = None
    transcript: str | None = None
    support_summary: str | None = None
    resolution_status: str | None = None
    suggested_solution: str | None = None
    next_action: str | None = None
    actions_taken: list[dict] | None = None
    created_ticket_id: int | None = None
    created_at: datetime
    ended_at: datetime | None = None
    summary_generated_at: datetime | None = None


class TicketFollowupCallRequest(BaseModel):
    """An administrator's reason and optional E.164 demo-number override."""

    reason: str | None = None
    recipient_phone: str | None = None


class ConversationRelaySetupMessage(BaseModel):
    """First message Twilio sends when the ConversationRelay WebSocket
    connects — see https://www.twilio.com/docs/voice/conversationrelay/websocket-messages.
    customParameters carries whatever <Parameter> elements voice_client's
    TwiML included, which is how the opaque call token reaches us too
    (redundant with the call_token query param on the wss:// URL itself,
    on purpose —
    two independent ways to resolve the same Call row).
    """

    type: Literal["setup"]
    callSid: str
    customParameters: dict[str, str] = {}


class ConversationRelayPromptMessage(BaseModel):
    """One finalized (or partial, if `last` is False) chunk of the caller's
    transcribed speech. We only act on `last=True` chunks — see
    call_service's ConversationRelay turn loop.
    """

    type: Literal["prompt"]
    voicePrompt: str
    lang: str = "en-US"
    last: bool = True


class ConversationRelayInterruptMessage(BaseModel):
    type: Literal["interrupt"]
    utteranceUntilInterrupt: str = ""
    durationUntilInterruptMs: int = 0


class ConversationRelayDtmfMessage(BaseModel):
    type: Literal["dtmf"]
    digit: str
