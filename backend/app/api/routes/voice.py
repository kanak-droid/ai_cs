import asyncio
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


async def _check_twilio_signature(request: Request) -> dict:
    """Twilio signs every webhook request (TwiML fetch, status callback)
    with an X-Twilio-Signature header — HMAC-SHA1 over the exact request
    URL plus its POST params, keyed by TWILIO_AUTH_TOKEN (see
    https://www.twilio.com/docs/usage/webhooks/webhooks-security). This is
    real, strong authentication. The opaque per-call token in the URL
    identifies a call, while this signature proves the request came from
    Twilio. ConversationRelay applies the same signature header to its
    WebSocket upgrade, which is checked separately below.

    Reconstructs the URL from VOICE_PUBLIC_BASE_URL rather than trusting
    request.url directly — behind a tunnel (ngrok) or reverse proxy,
    request.url often reports the internal http://localhost scheme/host
    Twilio never actually saw, which would make every signature fail;
    VOICE_PUBLIC_BASE_URL is the externally-visible URL we told Twilio to
    call in the first place (see voice_client.create_call), so rebuilding
    against it matches exactly what Twilio signed.
    """
    form = await request.form()
    if not settings.VOICE_VALIDATE_TWILIO_SIGNATURE:
        return dict(form)
    signature = request.headers.get("X-Twilio-Signature", "")
    public_url = f"{settings.VOICE_PUBLIC_BASE_URL}{request.url.path}"
    if request.url.query:
        public_url += f"?{request.url.query}"

    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    if not validator.validate(public_url, dict(form), signature):
        raise ForbiddenError("Invalid Twilio request signature")
    return dict(form)


def _check_twilio_websocket_signature(websocket: WebSocket) -> bool:
    """Validates the signed ConversationRelay WebSocket upgrade request."""
    if not settings.VOICE_VALIDATE_TWILIO_SIGNATURE:
        return True
    token = websocket.query_params.get("call_token")
    signature = websocket.headers.get("X-Twilio-Signature", "")
    if not token or not signature:
        return False
    scheme = "wss" if settings.VOICE_PUBLIC_BASE_URL.startswith("https") else "ws"
    host = settings.VOICE_PUBLIC_BASE_URL.split("://", 1)[-1]
    public_url = f"{scheme}://{host}/api/voice/conversation-relay?call_token={token}"
    return RequestValidator(settings.TWILIO_AUTH_TOKEN).validate(public_url, {}, signature)


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
    call_token: str,
    db: Session = Depends(get_db),
) -> Response:
    """Twilio fetches this the moment the outbound call connects (see
    voice_client.create_call's `url` param) and expects TwiML back —
    handing the call straight to ConversationRelay.
    """
    form = await _check_twilio_signature(request)
    call = call_service.get_call_by_relay_token(db, call_token)
    call_service.verify_twilio_call_sid(call, form.get("CallSid"))
    return Response(content=call_service.generate_connect_twiml(call), media_type="application/xml")


@router.post("/api/voice/status-callback")
async def status_callback(
    request: Request,
    call_token: str,
    db: Session = Depends(get_db),
) -> dict:
    form = await _check_twilio_signature(request)
    call = call_service.get_call_by_relay_token(db, call_token)
    call_service.verify_twilio_call_sid(call, form.get("CallSid"))
    call_service.handle_status_callback(db, call.id, form.get("CallStatus", ""))
    return {"status": "ok"}


@router.websocket("/api/voice/conversation-relay")
async def conversation_relay(
    websocket: WebSocket,
    call_token: str,
    db: Session = Depends(get_db),
) -> None:
    """ConversationRelay's WebSocket — held open for the whole call. Twilio
    sends one 'setup' message, then one 'prompt' per caller utterance
    (interim ones with last=False, which we ignore, then a final one with
    last=True), plus an 'interrupt' message the moment the caller talks
    over the agent. See call_service.py's module docstring for why the
    conversation's SessionContext/history lives here (per-connection)
    rather than in a stateless service function like chat's.

    Handling 'interrupt' is the reason this loop is structured around a
    background task rather than one straight-line
    receive -> process -> reply per iteration: ConversationRelay itself
    already stops *audio playback* the instant it detects the caller
    speaking (interruptible="any" — see generate_connect_twiml), but a
    naive await-everything loop would still be blocked inside a slow
    run_conversation_turn call when that interrupt message arrives,
    wouldn't read it until the current turn finished, and would then
    dutifully send the now-stale reply anyway — which is exactly what
    "the AI doesn't listen and keeps talking" turned out to be. `turn_id`
    is bumped on every interrupt and every new finalized prompt; a turn's
    reply is only ever sent if `turn_id` still matches what it was when
    that turn started, so a superseded turn's answer is silently dropped
    instead of spoken. `_lock` serializes the actual DB/LLM work itself
    (SQLAlchemy Sessions aren't safe for concurrent use across threads) —
    it does not block the receive loop, only the turn-processing task, so
    a fast interrupt is still noticed immediately even while a slow turn
    is still running in the background.
    """
    if not _check_twilio_websocket_signature(websocket):
        await websocket.close(code=1008)
        return

    await websocket.accept()

    try:
        call = call_service.get_call_by_relay_token(db, call_token)
        setup_message = await websocket.receive_json()
        if setup_message.get("type") != "setup":
            await websocket.close(code=1008)
            return
        call_service.verify_twilio_call_sid(call, setup_message.get("callSid"))
        setup_token = (setup_message.get("customParameters") or {}).get("call_token")
        if setup_token and setup_token != call_token:
            await websocket.close(code=1008)
            return
        call, ctx, history = call_service.start_conversation(db, call.id)
    except Exception:
        logger.exception("Failed to start conversation for call token %s", call_token)
        await websocket.close(code=1011)
        return

    turn_id = 0
    lock = asyncio.Lock()

    async def process_turn(user_message: str, my_turn_id: int) -> None:
        nonlocal turn_id
        async with lock:
            if my_turn_id != turn_id:
                return  # superseded before we even started this turn's work
            token_queue: asyncio.Queue[str] = asyncio.Queue()
            event_loop = asyncio.get_running_loop()

            def enqueue_token(token: str) -> None:
                """Safely forwards a blocking OpenRouter SSE chunk to this loop."""
                if token:
                    event_loop.call_soon_threadsafe(token_queue.put_nowait, token)

            generation_task = asyncio.create_task(
                asyncio.to_thread(
                    call_service.stream_conversation_turn,
                    db,
                    call,
                    ctx,
                    history,
                    user_message,
                    on_token=enqueue_token,
                )
            )
            try:
                while not generation_task.done():
                    try:
                        token = await asyncio.wait_for(token_queue.get(), timeout=0.05)
                    except TimeoutError:
                        continue
                    if my_turn_id == turn_id:
                        await websocket.send_json({"type": "text", "token": token, "last": False})
                await generation_task
                while not token_queue.empty():
                    token = token_queue.get_nowait()
                    if my_turn_id == turn_id:
                        await websocket.send_json({"type": "text", "token": token, "last": False})
            except Exception:
                logger.exception("Turn failed for call %s", call.id)
                if my_turn_id == turn_id:
                    await websocket.send_json(
                        {
                            "type": "text",
                            "token": "Sorry, I'm having trouble right now — could you say that again?",
                            "last": False,
                        }
                    )
        if my_turn_id != turn_id:
            return  # caller interrupted or spoke again while this was generating — never speak a stale reply
        await websocket.send_json({"type": "text", "token": "", "last": True})

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "interrupt":
                turn_id += 1
                continue

            if msg_type == "prompt":
                if not message.get("last", True):
                    continue  # interim transcript — wait for the finalized one
                user_message = message.get("voicePrompt", "")
                if not user_message:
                    continue
                turn_id += 1
                # Fire-and-forget: the loop goes straight back to
                # receive_json() so a following interrupt/prompt can still
                # supersede this one instead of waiting behind it.
                asyncio.create_task(process_turn(user_message, turn_id))
                continue

            if msg_type == "error":
                logger.warning(
                    "ConversationRelay error for call %s: %s", call.id, message.get("description")
                )

            # "dtmf": nothing for us to do — dtmfDetection isn't enabled in
            # generate_connect_twiml.

    except WebSocketDisconnect:
        pass
