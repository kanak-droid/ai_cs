from typing import Literal

from pydantic import BaseModel


class RequestCallBody(BaseModel):
    # Same client-generated id as ChatRequest.session_id — lets the call
    # pick up context from whatever the astrologer already told the text
    # bot in this webview visit. Optional: the "Request a call" button can
    # be shown with no prior chat at all.
    session_id: str | None = None


class RequestCallResponse(BaseModel):
    call_id: int
    status: str


class ConversationRelaySetupMessage(BaseModel):
    """First message Twilio sends when the ConversationRelay WebSocket
    connects — see https://www.twilio.com/docs/voice/conversationrelay/websocket-messages.
    customParameters carries whatever <Parameter> elements voice_client's
    TwiML included, which is how call_id reaches us here too (redundant
    with the call_id query param on the wss:// URL itself, on purpose —
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
