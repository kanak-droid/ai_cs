import logging

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator

from app.api.deps import get_current_astrologer, get_db
from app.core.config import settings
from app.core.errors import ForbiddenError
from app.core.security import AstrologerContext
from app.schemas.voice import RequestCallBody, RequestCallResponse
from app.services import call_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice"])


def _check_shared_secret(secret: str | None) -> None:
    # Same "unconfigured secret blocks the webhook entirely" convention as
    # zoho_webhook.py — this route stays inert (403ing every request) until
    # TWILIO_WEBHOOK_SECRET is actually set, rather than silently trusting
    # an unauthenticated caller by default.
    if not settings.TWILIO_WEBHOOK_SECRET or secret != settings.TWILIO_WEBHOOK_SECRET:
        raise ForbiddenError("Invalid or missing webhook secret")


async def _check_twilio_signature(request: Request) -> dict:
    """Twilio signs every webhook request (TwiML fetch, status callback)
    with an X-Twilio-Signature header — HMAC-SHA1 over the exact request
    URL plus its POST params, keyed by TWILIO_AUTH_TOKEN (see
    https://www.twilio.com/docs/usage/webhooks/webhooks-security). This is
    real, strong authentication — unlike the shared-secret query param
    (_check_shared_secret), which is only a defense-in-depth backstop here
    and the WebSocket route's *sole* check below, since a WS upgrade isn't
    covered by this same signing scheme.

    Reconstructs the URL from VOICE_PUBLIC_BASE_URL rather than trusting
    request.url directly — behind a tunnel (ngrok) or reverse proxy,
    request.url often reports the internal http://localhost scheme/host
    Twilio never actually saw, which would make every signature fail;
    VOICE_PUBLIC_BASE_URL is the externally-visible URL we told Twilio to
    call in the first place (see voice_client.create_call), so rebuilding
    against it matches exactly what Twilio signed.
    """
    form = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    public_url = f"{settings.VOICE_PUBLIC_BASE_URL}{request.url.path}"
    if request.url.query:
        public_url += f"?{request.url.query}"

    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    if not validator.validate(public_url, dict(form), signature):
        raise ForbiddenError("Invalid Twilio request signature")
    return dict(form)


@router.post("/api/voice/request-call", response_model=RequestCallResponse)
def request_call(
    body: RequestCallBody,
    astrologer: AstrologerContext = Depends(get_current_astrologer),
    db: Session = Depends(get_db),
) -> RequestCallResponse:
    call = call_service.request_call(db, astrologer, session_id=body.session_id)
    return RequestCallResponse(call_id=call.id, status=call.status.value)


@router.post("/api/voice/twiml")
async def twiml(
    request: Request,
    call_id: int,
    secret: str | None = None,
    db: Session = Depends(get_db),
) -> Response:
    """Twilio fetches this the moment the outbound call connects (see
    voice_client.create_call's `url` param) and expects TwiML back —
    handing the call straight to ConversationRelay.
    """
    _check_shared_secret(secret)
    await _check_twilio_signature(request)
    call = call_service.get_call(db, call_id)
    return Response(content=call_service.generate_connect_twiml(call), media_type="application/xml")


@router.post("/api/voice/status-callback")
async def status_callback(
    request: Request,
    call_id: int,
    secret: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    _check_shared_secret(secret)
    form = await _check_twilio_signature(request)
    call_service.handle_status_callback(db, call_id, form.get("CallStatus", ""))
    return {"status": "ok"}


@router.websocket("/api/voice/conversation-relay")
async def conversation_relay(
    websocket: WebSocket,
    call_id: int,
    secret: str | None = None,
    db: Session = Depends(get_db),
) -> None:
    """ConversationRelay's WebSocket — held open for the whole call. Twilio
    sends one 'setup' message, then one 'prompt' per caller utterance
    (interim ones with last=False, which we ignore, then a final one with
    last=True); we reply with a 'text' message per turn. See
    call_service.py's module docstring for why the conversation's
    SessionContext/history lives here (per-connection) rather than in a
    stateless service function like chat's.
    """
    if not settings.TWILIO_WEBHOOK_SECRET or secret != settings.TWILIO_WEBHOOK_SECRET:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    try:
        call, ctx, history = call_service.start_conversation(db, call_id)
    except Exception:
        logger.exception("Failed to start conversation for call %s", call_id)
        await websocket.close(code=1011)
        return

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "prompt":
                if not message.get("last", True):
                    continue  # interim transcript — wait for the finalized one
                user_message = message.get("voicePrompt", "")
                if not user_message:
                    continue
                try:
                    result = call_service.run_conversation_turn(db, call, ctx, history, user_message)
                    reply = result.reply
                except Exception:
                    logger.exception("Turn failed for call %s", call_id)
                    reply = "Sorry, I'm having trouble right now — could you say that again?"
                await websocket.send_json({"type": "text", "token": reply, "last": True})

            elif msg_type == "error":
                logger.warning("ConversationRelay error for call %s: %s", call_id, message.get("description"))

            # "interrupt" and "dtmf" messages: nothing for us to do —
            # ConversationRelay already stops playback on interrupt itself,
            # and dtmfDetection isn't enabled in generate_connect_twiml.

    except WebSocketDisconnect:
        pass
