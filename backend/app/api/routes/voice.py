import logging

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_astrologer, get_db
from app.core.config import settings
from app.core.errors import ForbiddenError
from app.core.security import AstrologerContext
from app.schemas.voice import (
    RequestCallBody,
    RequestCallResponse,
    VapiChatCompletionChoice,
    VapiChatCompletionResponse,
    VapiChatMessage,
    VapiCustomLLMRequest,
)
from app.services import call_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice"])


def _check_vapi_secret(x_vapi_secret: str | None) -> None:
    # Same "unconfigured secret blocks the webhook entirely" convention as
    # zoho_webhook.py — the prototype stays inert (401ing every Vapi
    # request) until VAPI_WEBHOOK_SECRET is actually set, rather than
    # silently trusting an unauthenticated caller by default. Set the same
    # value in Vapi's dashboard alongside each server URL below (the exact
    # header Vapi lets you attach wasn't confirmed against a live account
    # as of 2026-09-03 — if Vapi's plan/UI doesn't support a custom header,
    # this'll need to become an URL-embedded token instead).
    if not settings.VAPI_WEBHOOK_SECRET or x_vapi_secret != settings.VAPI_WEBHOOK_SECRET:
        raise ForbiddenError("Invalid or missing Vapi webhook secret")


@router.post("/api/voice/request-call", response_model=RequestCallResponse)
def request_call(
    body: RequestCallBody,
    astrologer: AstrologerContext = Depends(get_current_astrologer),
    db: Session = Depends(get_db),
) -> RequestCallResponse:
    call = call_service.request_call(db, astrologer, session_id=body.session_id)
    return RequestCallResponse(call_id=call.id, status=call.status.value)


@router.post("/api/voice/custom-llm", response_model=VapiChatCompletionResponse)
def custom_llm(
    body: VapiCustomLLMRequest,
    db: Session = Depends(get_db),
    x_vapi_secret: str | None = Header(default=None),
) -> VapiChatCompletionResponse:
    """Vapi's Custom LLM hook — called once per assistant turn during a live
    call, in place of Vapi's own built-in LLM. We run the exact same
    orchestrator turn as text chat (see call_service.handle_custom_llm_turn)
    — tool calls (get_payout_status, create_support_ticket, etc.) execute
    synchronously inside that call, so by the time we reply here the turn's
    tools have already run; Vapi never sees or calls them itself.

    Non-streaming: returns one complete JSON chat-completion response
    rather than an SSE stream. Simpler for a prototype, at the cost of the
    caller hearing dead air for the full orchestrator round-trip
    (STT->Gemini(+tool calls)->this response->TTS) instead of the model's
    first tokens starting to speak immediately — acceptable while proving
    the agent/tooling out; only worth streaming once the fixed round-trip
    itself is fast enough to matter.
    """
    _check_vapi_secret(x_vapi_secret)

    call_id = body.call.get("id")
    if not call_id:
        # Can't route this turn to a Call row at all — surface a spoken
        # error rather than a raw 4xx, since Vapi will just read back
        # whatever we return as the assistant's next line.
        return VapiChatCompletionResponse(
            id="error",
            choices=[
                VapiChatCompletionChoice(
                    message=VapiChatMessage(
                        role="assistant",
                        content="Sorry, I'm having trouble pulling up your account right now.",
                    )
                )
            ],
        )

    result = call_service.handle_custom_llm_turn(db, call_id, body.messages)
    return VapiChatCompletionResponse(
        id=f"call-{call_id}",
        choices=[
            VapiChatCompletionChoice(message=VapiChatMessage(role="assistant", content=result.reply))
        ],
    )


@router.post("/api/voice/events")
async def voice_events(
    request: Request,
    db: Session = Depends(get_db),
    x_vapi_secret: str | None = Header(default=None),
) -> dict:
    """Vapi's server-URL webhook — call lifecycle only (status-update,
    end-of-call-report, ...), never the assistant's actual replies (that's
    /api/voice/custom-llm above). Raw dict body rather than a typed schema:
    the message shape genuinely varies by event type and we only read a
    handful of fields out of it (see call_service.handle_lifecycle_event) —
    modeling every Vapi event type is more upfront work than a prototype
    needs.
    """
    _check_vapi_secret(x_vapi_secret)

    body = await request.json()
    message = body.get("message") or {}
    call_service.handle_lifecycle_event(db, message)
    return {"status": "ok"}
