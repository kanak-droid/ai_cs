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

ConversationRelay holds one WebSocket connection open for the whole call
and only sends each new utterance (not the full history) each time, so
app/api/routes/voice.py's WebSocket handler owns the conversation's
SessionContext/history for the connection's lifetime and calls
run_conversation_turn once per caller utterance.

Voice turns use OpenRouter server-sent events: tool-only completions stay
inside the backend, while final spoken-answer chunks are sent to
ConversationRelay immediately. This lets TTS begin before the full reply
is complete. End-of-call outcomes use the same provider and are stored on
the Call row for the customer-support dashboard.
"""

import json
import logging
import re
import secrets
import threading
from collections.abc import Callable
from typing import cast
from xml.sax.saxutils import escape

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.client import AgentClient, StreamingAgentClient
from app.agent.context import SessionContext
from app.agent.openrouter_client import get_voice_agent_client
from app.agent.orchestrator import HistoryTurn, run_chat_turn, run_streaming_chat_turn
from app.core.config import settings
from app.core.errors import ForbiddenError, NotFoundError
from app.core.security import AstrologerContext
from app.core.time import utcnow
from app.integrations import voice_client
from app.models.astrologer import Astrologer
from app.models.call import Call
from app.models.enums import CallStatus
from app.models.ticket import Ticket
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
    "Hindi": (
        "hi-IN",
        "IvLWq57RKibBrqZGpQrC",
        "Namaste {name}, main AstroHelp support se bol raha hoon. Main aapki kaise madad kar sakta hoon?",
    ),
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
_OUTCOME_STATUSES = {"resolved", "follow_up_required", "escalated", "unknown", "not_connected"}
_SUMMARY_TRANSCRIPT_LIMIT = 12_000


def _create_call(
    db: Session,
    *,
    astrologer_row: Astrologer,
    session_id: str | None = None,
    ticket_id: int | None = None,
    triggered_by: str,
    recipient_phone: str | None = None,
) -> Call:
    """Persists one outbound call and submits it to Twilio after a DB flush."""
    selected_phone = recipient_phone or astrologer_row.phone
    call = Call(
        astrologer_id=astrologer_row.id,
        phone_number=selected_phone,
        ticket_id=ticket_id,
        triggered_by=triggered_by,
        session_id=session_id,
        relay_token=secrets.token_urlsafe(32),
        status=CallStatus.QUEUED,
    )
    db.add(call)
    db.flush()
    # Keep the freshly-created token in a local non-optional variable. Old
    # rows predate relay_token, but every new outbound call must have one.
    if call.relay_token is None:
        raise RuntimeError("New voice call did not receive a relay token")
    result = voice_client.create_call(selected_phone, call.relay_token)
    call.twilio_call_sid = result.twilio_call_sid
    db.commit()
    db.refresh(call)
    return call


def request_call(
    db: Session, astrologer: AstrologerContext, *, session_id: str | None = None
) -> Call:
    astrologer_row = db.get(Astrologer, astrologer.astrologer_id)
    if astrologer_row is None:
        raise NotFoundError(f"No astrologer {astrologer.astrologer_id}")

    return _create_call(
        db,
        astrologer_row=astrologer_row,
        session_id=session_id,
        triggered_by="user_request",
    )


def request_ticket_followup_call(
    db: Session,
    *,
    ticket: Ticket,
    triggered_by: str,
    recipient_phone: str | None = None,
) -> Call:
    """Starts a ticket-specific outbound follow-up call using the ticket owner."""
    astrologer_row = db.get(Astrologer, ticket.astrologer_id)
    if astrologer_row is None:
        raise NotFoundError(f"No astrologer found for ticket {ticket.id}")
    return _create_call(
        db,
        astrologer_row=astrologer_row,
        ticket_id=ticket.id,
        triggered_by=triggered_by,
        recipient_phone=recipient_phone,
    )


def get_call(db: Session, call_id: int) -> Call:
    call = db.get(Call, call_id)
    if call is None:
        raise NotFoundError(f"No call {call_id}")
    return call


def get_call_by_relay_token(db: Session, relay_token: str) -> Call:
    """Returns a call by its opaque token carried in Twilio callback URLs."""
    call = db.scalar(select(Call).where(Call.relay_token == relay_token))
    if call is None:
        raise NotFoundError("Unknown voice call")
    return call


def list_calls_for_ticket(db: Session, *, ticket_id: int) -> list[Call]:
    """Returns ticket follow-up calls newest first for dashboard/API use."""
    return list(
        db.scalars(select(Call).where(Call.ticket_id == ticket_id).order_by(Call.created_at.desc()))
    )


def list_recent_calls(db: Session, *, limit: int = 100) -> list[Call]:
    """Returns recent phone calls for the support dashboard's call queue."""
    return list(db.scalars(select(Call).order_by(Call.created_at.desc()).limit(limit)))


def verify_twilio_call_sid(call: Call, call_sid: str | None) -> None:
    """Rejects a webhook/relay event whose Call SID is not this call's SID."""
    if not call_sid or call_sid != call.twilio_call_sid:
        raise ForbiddenError("Twilio call identity does not match")


def generate_connect_twiml(call: Call) -> str:
    """The XML Twilio fetches to learn what to do with the call — hands it
    straight to ConversationRelay, pointed at our WebSocket. The opaque
    relay token is
    passed both ways on purpose: once on the wss:// URL's own query string
    (so the WebSocket route can resolve the Call before even reading the
    first message) and again as a <Parameter>, which Twilio echoes back
    inside the setup message itself — a second, independent confirmation
    that doesn't rely on the query string surviving whatever proxy/tunnel
    sits in front of us in a given environment.
    """
    ws_scheme = "wss" if settings.VOICE_PUBLIC_BASE_URL.startswith("https") else "ws"
    host = settings.VOICE_PUBLIC_BASE_URL.split("://", 1)[-1]
    ws_url = f"{ws_scheme}://{host}/api/voice/conversation-relay?call_token={call.relay_token}"

    language, voice, greeting_template = _VOICE_BY_LANGUAGE.get(
        call.astrologer.language, _DEFAULT_VOICE
    )
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
        f'<Parameter name="call_token" value="{escape(call.relay_token or "")}"/>'
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
        history.append(
            HistoryTurn(role="astrologer", text=f"[Earlier chat with support bot]\n{prior_chat}")
        )

    if call.status == CallStatus.QUEUED:
        call.status = CallStatus.IN_PROGRESS
        db.commit()

    return call, ctx, history


def _ticket_context(call: Call) -> str:
    """Builds the ticket-only context appended to a proactive voice turn."""
    if call.ticket is None:
        return ""
    return (
        f" This is a proactive follow-up about support ticket #{call.ticket.id}. "
        f"Its category is '{call.ticket.category}' and the reported issue is "
        f"'{call.ticket.description}'. Acknowledge that context without claiming it is resolved."
    )


def _persist_conversation_turn(
    db: Session,
    *,
    call: Call,
    history: list[HistoryTurn],
    user_message: str,
    reply: str,
    trace: list,
    metadata: dict,
) -> str:
    """Stores one completed voice turn and its tool actions on the call."""
    clean_reply = _strip_markdown(reply)
    history.append(HistoryTurn(role="astrologer", text=user_message))
    history.append(HistoryTurn(role="assistant", text=clean_reply))
    call.transcript = (
        call.transcript or ""
    ) + f"\nAstrologer: {user_message}\nAgent: {clean_reply}"
    actions = list(call.actions_taken or [])
    actions.extend({"tool": step.tool, "ok": step.ok, "summary": step.summary} for step in trace)
    call.actions_taken = actions or None
    if metadata.get("created_ticket_id"):
        call.created_ticket_id = metadata["created_ticket_id"]
    db.commit()
    return clean_reply


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
    ticket_context = _ticket_context(call)
    result = run_chat_turn(
        client or get_voice_agent_client(),
        ctx,
        user_message,
        history=history,
        extra_instructions=f"{_VOICE_INSTRUCTIONS}{ticket_context}",
    )
    return _persist_conversation_turn(
        db,
        call=call,
        history=history,
        user_message=user_message,
        reply=result.reply,
        trace=result.trace,
        metadata=result.metadata,
    )


def stream_conversation_turn(
    db: Session,
    call: Call,
    ctx: SessionContext,
    history: list[HistoryTurn],
    user_message: str,
    *,
    on_token: Callable[[str], None],
    client: AgentClient | None = None,
) -> str:
    """Streams a final model answer while retaining the same secure tools.

    Test clients and any future non-streaming provider gracefully use the
    original complete-response path, so availability does not depend on SSE.
    """
    agent_client = client or get_voice_agent_client()
    instructions = f"{_VOICE_INSTRUCTIONS}{_ticket_context(call)}"
    if hasattr(agent_client, "stream_generate"):
        result = run_streaming_chat_turn(
            cast(StreamingAgentClient, agent_client),
            ctx,
            user_message,
            history=history,
            extra_instructions=instructions,
            on_text=lambda token: on_token(_strip_markdown(token)),
        )
    else:
        result = run_chat_turn(
            agent_client,
            ctx,
            user_message,
            history=history,
            extra_instructions=instructions,
        )
        on_token(_strip_markdown(result.reply))

    return _persist_conversation_turn(
        db,
        call=call,
        history=history,
        user_message=user_message,
        reply=result.reply,
        trace=result.trace,
        metadata=result.metadata,
    )


def _fallback_call_outcome(call: Call) -> dict[str, str]:
    """Returns a useful dashboard outcome when LLM summarization is unavailable."""
    transcript = (call.transcript or "").strip()
    if not transcript:
        return {
            "summary": "The call ended without a recorded conversation.",
            "resolution_status": "not_connected",
            "suggested_solution": "No solution could be discussed.",
            "next_action": "Try contacting the customer again.",
        }
    last_agent_reply = transcript.rsplit("Agent:", maxsplit=1)[-1].strip()
    return {
        "summary": "A support call was completed. Review the transcript for the full discussion.",
        "resolution_status": "unknown",
        "suggested_solution": last_agent_reply or "No specific solution was captured.",
        "next_action": "Review the call and follow up if the issue remains unresolved.",
    }


def _normalise_call_outcome(raw_summary: str, call: Call) -> dict[str, str]:
    """Validates model JSON and fills omissions with deterministic defaults."""
    fallback = _fallback_call_outcome(call)
    try:
        parsed = json.loads(raw_summary)
    except (TypeError, json.JSONDecodeError):
        return fallback
    if not isinstance(parsed, dict):
        return fallback
    outcome = {
        field: str(parsed.get(field) or fallback[field]).strip()
        for field in ("summary", "resolution_status", "suggested_solution", "next_action")
    }
    if outcome["resolution_status"] not in _OUTCOME_STATUSES:
        outcome["resolution_status"] = fallback["resolution_status"]
    return outcome


def _infer_deterministic_status(actions: list[dict] | None) -> str | None:
    """Returns a resolution_status when tool outcomes are unambiguous."""
    if not actions:
        return None
    for action in actions:
        tool = action.get("tool", "")
        ok = action.get("ok", False)
        if tool == "create_support_ticket" and ok:
            return "escalated"
        if tool == "mark_issue_resolved" and ok:
            return "resolved"
    return None


def _build_summary_prompt(call: Call) -> str:
    """Builds a detailed prompt with deterministic hints for the summary model."""
    actions = call.actions_taken or []
    deterministic_hint = _infer_deterministic_status(actions)

    hints: list[str] = []
    if deterministic_hint == "escalated":
        hints.append(
            "IMPORTANT: The agent successfully created a support ticket during this "
            "call. This strongly indicates resolution_status should be 'escalated'."
        )
    elif deterministic_hint == "resolved":
        hints.append(
            "IMPORTANT: The agent called mark_issue_resolved during this call. "
            "This strongly indicates resolution_status should be 'resolved'."
        )

    tool_names = [a.get("tool", "") for a in actions if a.get("ok")]
    if tool_names:
        hints.append(f"Tools used successfully: {', '.join(tool_names)}.")

    sections = [
        "Summarize this completed customer-support phone call for an internal "
        "dashboard read by human CS agents who may call this person back.",
        "Do not invent facts. resolution_status must be one of: resolved, "
        "follow_up_required, escalated, unknown.",
    ]
    if hints:
        sections.append("\n".join(hints))
    sections.append(f"Actions taken: {json.dumps(actions)}")
    sections.append(f"Transcript:\n{call.transcript[-_SUMMARY_TRANSCRIPT_LIMIT:]}")
    return "\n\n".join(sections)


def _generate_summary_in_background(call_id: int) -> None:
    """Runs summary generation in a daemon thread with its own DB session."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        call = db.get(Call, call_id)
        if call is None or call.summary_generated_at is not None:
            return

        fallback = _fallback_call_outcome(call)
        outcome = fallback
        if settings.OPENROUTER_API_KEY and call.transcript:
            prompt = _build_summary_prompt(call)
            try:
                raw_summary = get_voice_agent_client().generate_call_summary(prompt=prompt)
                outcome = _normalise_call_outcome(raw_summary, call)
                deterministic = _infer_deterministic_status(call.actions_taken)
                if deterministic:
                    outcome["resolution_status"] = deterministic
            except Exception:
                logger.exception("Call outcome generation failed for call %s", call_id)

        call.support_summary = outcome["summary"]
        call.resolution_status = outcome["resolution_status"]
        call.suggested_solution = outcome["suggested_solution"]
        call.next_action = outcome["next_action"]
        call.summary_generated_at = utcnow()
        db.commit()
    except Exception:
        logger.exception("Background summary thread failed for call %s", call_id)
    finally:
        db.close()


def generate_call_outcome_summary(db: Session, call: Call) -> None:
    """Generates the customer-support dashboard outcome exactly once per call.

    Spawns a background thread so the Twilio status-callback webhook responds
    immediately — summary latency no longer blocks the webhook response.
    """
    if call.summary_generated_at is not None:
        return
    thread = threading.Thread(
        target=_generate_summary_in_background,
        args=(call.id,),
        daemon=True,
    )
    thread.start()


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
    if twilio_status in _TERMINAL_TWILIO_STATUSES:
        generate_call_outcome_summary(db, call)
