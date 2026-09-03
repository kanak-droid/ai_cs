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


class VapiChatMessage(BaseModel):
    role: str
    content: str


class VapiCustomLLMRequest(BaseModel):
    """Vapi's Custom LLM feature POSTs an OpenAI chat/completions-shaped
    body here for every assistant turn. The exact placement of call context
    on this payload wasn't confirmed against a live Vapi account as of
    2026-09-03 (Vapi's own docs describe it only loosely) — `call` is
    typed loose (plain dict) so the route can read whatever subset of
    `call.id` actually shows up rather than failing schema validation on a
    field we guessed wrong. See call_service.handle_custom_llm_turn for how
    the call is actually resolved (by matching `call.id` against our own
    Call.vapi_call_id, not by trusting any echoed metadata).
    """

    messages: list[VapiChatMessage]
    call: dict = {}
    stream: bool = False


class VapiChatCompletionChoice(BaseModel):
    index: int = 0
    message: VapiChatMessage
    finish_reason: str = "stop"


class VapiChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str = "astrohelp-agent"
    choices: list[VapiChatCompletionChoice]
