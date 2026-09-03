"""Bridges the AI phone call to the exact same agent brain as text chat —
see app/services/chat_service.py, which this deliberately mirrors. The only
real new logic here is telephony bookkeeping (request_call,
handle_status_callback) and TwiML generation; run_conversation_turn is a
thin per-turn wrapper around the same run_chat_turn function
chat_service.handle_chat_turn calls.

Runs on OpenRouter (app/agent/openrouter_client.py), not Gemini — a
deliberate split from chat, not an oversight: the phone agent and the
text-chat agent are free to run on different model providers since only
the tool-calling loop (orchestrator.py) and tool_registry.py are actually
shared between them.

Unlike the earlier Vapi-based design, there is no single stateless
request/response turn function here — ConversationRelay holds one
WebSocket connection open for the whole call and only sends each new
utterance (not the full history) each time, so app/api/routes/voice.py's
WebSocket handler owns the conversation's SessionContext/history for the
connection's lifetime and calls run_conversation_turn once per caller
utterance.

Latency, reported live 2026-09-04: run_conversation_turn is NOT
streamed — it waits for the whole reply (including any tool-call round
trip) before returning, and the WebSocket handler sends it to
ConversationRelay as one text message, so TTS can't start speaking the
first sentence while the rest is still being generated. speechTimeout
below is tuned down from Twilio's cautious "auto" default as a partial,
low-risk mitigation; true token-level streaming through the tool-calling
loop would help more but is a real orchestrator-level redesign, not
attempted here yet.
"""

import logging
import re
from xml.sax.saxutils import escape

from sqlalchemy.orm import Session

from app.agent.client import AgentClient
from app.agent.context import SessionContext
from app.agent.openrouter_client import get_voice_agent_client
from app.agent.orchestrator import HistoryTurn, run_chat_turn
from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.security import AstrologerContext
from app.core.time import utcnow
from app.integrations import voice_client
from app.models.astrologer import Astrologer
from app.models.call import Call
from app.models.enums import CallStatus
from app.services import chat_session_service

logger = logging.getLogger(__name__)

# ConversationRelay language code + a confirmed-working Twilio-listed voice
# id per Astrologer.language value (see generate_connect_twiml) — None for
# the voice means "use ttsProvider's own default for that language",
# ElevenLabs by default. Hindi's voice id verified against Twilio's own
# ConversationRelay voice-configuration docs (2026-09-03), not guessed —
# add an entry here for any other Astrologer.language value that needs a
# non-English call; anything unmapped falls back to English below. The
# welcome greeting is keyed the same way — the `language` attribute sets
# STT/TTS for the *whole* call including this greeting, so playing English
# words under a Hindi voice/language setting would come out garbled;
# {name} is filled in by generate_connect_twiml.
_VOICE_BY_LANGUAGE: dict[str, tuple[str, str | None, str]] = {
    "Hindi": ("hi-IN", "IvLWq57RKibBrqZGpQrC", "Namaste {name}, main AstroHelp support se bol raha hoon. Main aapki kaise madad kar sakta hoon?"),
    "English": ("en-US", None, "Hi {name}, this is AstroHelp support. How can I help you today?"),
}
_DEFAULT_VOICE = _VOICE_BY_LANGUAGE["English"]

# Told to the model only on phone calls (see run_conversation_turn) — chat
# has no equivalent constraint, since a chat UI renders markdown fine.
# ConversationRelay speaks whatever text we send verbatim, including any
# markdown syntax characters, so without this the TTS voice was literally
# reading out "asterisk asterisk" around emphasized words.
_VOICE_INSTRUCTIONS = (
    "You are speaking on a live phone call, not typing in a chat window. "
    "Reply in plain, natural spoken sentences only — never use markdown "
    "formatting (no asterisks, no bullet points or numbered lists, no "
    "headers, no bold/italic syntax). Say amounts and dates the way a "
    "person would say them aloud, not as a formatted table. "
    "If the astrologer keeps describing the same problem again in this "
    "call, do not repeat the exact same suggested resolution more than "
    "twice in total, regardless of their priority tier — after the second "
    "time, stop repeating yourself and instead offer to raise a support "
    "ticket (create_support_ticket) so a human can help."
)

_MARKDOWN_PATTERN = re.compile(r"[*_#`]+|^\s*[-•]\s+", flags=re.MULTILINE)


def _strip_markdown(text: str) -> str:
    """Defensive backstop for _VOICE_INSTRUCTIONS above — the model mostly
    complies with a plain-text instruction but not always, so this also
    strips the common markdown syntax characters outright before anything
    is ever sent to ConversationRelay to be spoken.
    """
    return _MARKDOWN_PATTERN.sub("", text)

# Twilio's own CallStatus values (status-callback's `CallStatus` form field)
# mapped onto our CallStatus enum — see
# https://www.twilio.com/docs/voice/twiml#callstatus-values.
_STATUS_FROM_TWILIO = {
    "queued": CallStatus.QUEUED,
    "initiated": CallStatus.QUEUED,
    "ringing": CallStatus.RINGING,
    "in-progress": CallStatus.IN_PROGRESS,
    "answered": CallStatus.IN_PROGRESS,
    "completed": CallStatus.ENDED,
    "busy": CallStatus.FAILED,
    "failed": CallStatus.FAILED,
    "no-answer": CallStatus.FAILED,
    "canceled": CallStatus.FAILED,
}
_TERMINAL_TWILIO_STATUSES = {"completed", "busy", "failed", "no-answer", "canceled"}


def request_call(db: Session, astrologer: AstrologerContext, *, session_id: str | None = None) -> Call:
    astrologer_row = db.get(Astrologer, astrologer.astrologer_id)
    if astrologer_row is None:
        raise NotFoundError(f"No astrologer {astrologer.astrologer_id}")

    call = Call(
        astrologer_id=astrologer.astrologer_id,
        phone_number=astrologer_row.phone,
        session_id=session_id,
        status=CallStatus.QUEUED,
    )
    db.add(call)
    db.flush()  # assigns call.id — voice_client bakes it into the TwiML/WebSocket URLs

    result = voice_client.create_call(astrologer_row.phone, call.id)
    call.twilio_call_sid = result.twilio_call_sid
    db.commit()
    db.refresh(call)
    return call


def get_call(db: Session, call_id: int) -> Call:
    call = db.get(Call, call_id)
    if call is None:
        raise NotFoundError(f"No call {call_id}")
    return call


def generate_connect_twiml(call: Call) -> str:
    """The XML Twilio fetches to learn what to do with the call — hands it
    straight to ConversationRelay, pointed at our WebSocket. call_id is
    passed both ways on purpose: once on the wss:// URL's own query string
    (so the WebSocket route can resolve the Call before even reading the
    first message) and again as a <Parameter>, which Twilio echoes back
    inside the setup message itself — a second, independent confirmation
    that doesn't rely on the query string surviving whatever proxy/tunnel
    sits in front of us in a given environment.
    """
    ws_scheme = "wss" if settings.VOICE_PUBLIC_BASE_URL.startswith("https") else "ws"
    host = settings.VOICE_PUBLIC_BASE_URL.split("://", 1)[-1]
    ws_url = f"{ws_scheme}://{host}/api/voice/conversation-relay?call_id={call.id}&secret={settings.TWILIO_WEBHOOK_SECRET}"

    language, voice, greeting_template = _VOICE_BY_LANGUAGE.get(call.astrologer.language, _DEFAULT_VOICE)
    voice_attr = f' voice="{escape(voice)}"' if voice else ""
    greeting = greeting_template.format(name=call.astrologer.name)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Connect>"
        f'<ConversationRelay url="{escape(ws_url)}" '
        # 700ms rather than the "auto" default — auto is deliberately
        # cautious about not cutting someone off mid-sentence, at the cost
        # of a longer pause before the agent starts responding after the
        # caller stops talking. 700 is close to Twilio's documented
        # minimum (600) without being right at the edge; worth raising
        # back up if callers start getting cut off mid-thought in
        # practice — see call_service.py's module docstring on latency.
        'speechTimeout="700" '
        # Explicit rather than relying on the (same-valued) documented
        # defaults — this exact behavior was reported broken once already
        # (see app/api/routes/voice.py's conversation_relay docstring for
        # the actual fix, which was server-side); spelling it out here
        # removes one more place a silent default change could regress it.
        'interruptible="any" interruptSensitivity="high" '
        f'language="{escape(language)}"{voice_attr} '
        f'welcomeGreeting="{escape(greeting)}">'
        f'<Parameter name="call_id" value="{call.id}"/>'
        "</ConversationRelay>"
        "</Connect></Response>"
    )


def start_conversation(db: Session, call_id: int) -> tuple[Call, SessionContext, list[HistoryTurn]]:
    """Called once, right after the ConversationRelay WebSocket's `setup`
    message arrives — builds the SessionContext and seeds history from any
    linked chat-app session, exactly mirroring chat_service.handle_chat_turn's
    _find_last_attachment_url/history handling, minus attachments (a phone
    call has no way to receive an image from the caller).
    """
    call = get_call(db, call_id)
    astrologer_row = db.get(Astrologer, call.astrologer_id)
    if astrologer_row is None:
        raise NotFoundError(f"No astrologer {call.astrologer_id}")

    ctx = SessionContext(
        astrologer_id=astrologer_row.id,
        name=astrologer_row.name,
        language=astrologer_row.language,
        db=db,
        session_id=call.session_id,
    )

    history: list[HistoryTurn] = []
    prior_chat = chat_session_service.get_transcript_text(db, call.session_id)
    if prior_chat:
        history.append(HistoryTurn(role="astrologer", text=f"[Earlier chat with support bot]\n{prior_chat}"))

    if call.status == CallStatus.QUEUED:
        call.status = CallStatus.IN_PROGRESS
        db.commit()

    return call, ctx, history


def run_conversation_turn(
    db: Session,
    call: Call,
    ctx: SessionContext,
    history: list[HistoryTurn],
    user_message: str,
    *,
    client: AgentClient | None = None,
) -> str:
    """One caller utterance -> one agent reply, returned as plain text
    ready to hand straight to ConversationRelay. `history` is mutated in
    place (the WebSocket route holds the one list for the whole call) so
    each subsequent turn sees everything said so far, same as chat's
    per-request history param but accumulated locally instead of resent by
    the client every time.
    """
    result = run_chat_turn(
        client or get_voice_agent_client(),
        ctx,
        user_message,
        history=history,
        extra_instructions=_VOICE_INSTRUCTIONS,
    )
    reply = _strip_markdown(result.reply)
    history.append(HistoryTurn(role="astrologer", text=user_message))
    history.append(HistoryTurn(role="assistant", text=reply))

    call.transcript = (call.transcript or "") + f"\nAstrologer: {user_message}\nAgent: {reply}"
    if result.metadata.get("created_ticket_id"):
        call.created_ticket_id = result.metadata["created_ticket_id"]
    db.commit()
    return reply


def handle_status_callback(db: Session, call_id: int, twilio_status: str) -> None:
    """One status-callback event from Twilio (see voice_client.create_call's
    status_callback_event list) — updates the Call row's lifecycle state.
    Unrecognized statuses are a no-op rather than an error, since Twilio's
    status set has grown before and a new/unmapped value shouldn't 500 the
    webhook.
    """
    call = db.get(Call, call_id)
    if call is None:
        logger.warning("Status callback for unknown call id %s", call_id)
        return

    mapped = _STATUS_FROM_TWILIO.get(twilio_status)
    if mapped is None:
        return

    call.status = mapped
    if twilio_status in _TERMINAL_TWILIO_STATUSES:
        call.ended_at = call.ended_at or utcnow()
        if twilio_status != "completed":
            call.ended_reason = twilio_status
    db.commit()
