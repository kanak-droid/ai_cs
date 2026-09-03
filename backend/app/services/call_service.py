"""Bridges the AI phone call to the exact same agent brain as text chat —
see app/services/chat_service.py, which this deliberately mirrors. The only
real new logic here is telephony bookkeeping (request_call,
handle_lifecycle_event); handle_custom_llm_turn is a thin adapter from
Vapi's OpenAI-shaped turn format onto run_chat_turn, the same function
chat_service.handle_chat_turn calls.
"""

import logging

from sqlalchemy.orm import Session

from app.agent.client import AgentClient, get_agent_client
from app.agent.context import SessionContext
from app.agent.orchestrator import ChatTurnResult, HistoryTurn, run_chat_turn
from app.core.errors import NotFoundError
from app.core.security import AstrologerContext
from app.core.time import utcnow
from app.integrations import voice_client
from app.models.astrologer import Astrologer
from app.models.call import Call
from app.models.enums import CallStatus
from app.schemas.voice import VapiChatMessage
from app.services import chat_session_service

logger = logging.getLogger(__name__)

_ROLE_FROM_OPENAI = {"user": "astrologer", "assistant": "assistant"}


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
    db.flush()  # assigns call.id, in case create_call ever needs to log against it

    result = voice_client.create_call(astrologer_row.phone, astrologer.astrologer_id)
    call.vapi_call_id = result.vapi_call_id
    db.commit()
    db.refresh(call)
    return call


def _get_call_by_vapi_id(db: Session, vapi_call_id: str) -> Call:
    call = db.query(Call).filter_by(vapi_call_id=vapi_call_id).one_or_none()
    if call is None:
        raise NotFoundError(f"No call for Vapi call id {vapi_call_id}")
    return call


def handle_custom_llm_turn(
    db: Session,
    vapi_call_id: str,
    messages: list[VapiChatMessage],
    *,
    client: AgentClient | None = None,
) -> ChatTurnResult:
    call = _get_call_by_vapi_id(db, vapi_call_id)
    astrologer_row = db.get(Astrologer, call.astrologer_id)
    if astrologer_row is None:
        raise NotFoundError(f"No astrologer {call.astrologer_id}")

    # Vapi resends the full turn history on every request (it's stateless
    # on our side, same as /api/chat) — the last "user" message is this
    # turn's new utterance, everything before it is history.
    turns = [m for m in messages if m.role in _ROLE_FROM_OPENAI]
    if not turns or turns[-1].role != "user":
        raise NotFoundError("Custom LLM request has no caller utterance to respond to")
    latest = turns[-1]
    prior = turns[:-1]

    agent_history = [HistoryTurn(role=_ROLE_FROM_OPENAI[m.role], text=m.content) for m in prior]

    # First turn of the call only: seed history with whatever the
    # astrologer already told the text bot in the linked chat-app session,
    # so the phone agent doesn't ask them to repeat their issue.
    if not agent_history:
        prior_chat = chat_session_service.get_transcript_text(db, call.session_id)
        if prior_chat:
            agent_history.append(
                HistoryTurn(role="astrologer", text=f"[Earlier chat with support bot]\n{prior_chat}")
            )

    ctx = SessionContext(
        astrologer_id=astrologer_row.id,
        name=astrologer_row.name,
        language=astrologer_row.language,
        db=db,
        session_id=call.session_id,
        has_prior_reply=any(t.role == "assistant" for t in agent_history),
    )
    result = run_chat_turn(client or get_agent_client(), ctx, latest.content, history=agent_history)

    call.transcript = (call.transcript or "") + f"\nAstrologer: {latest.content}\nAgent: {result.reply}"
    if result.metadata.get("created_ticket_id"):
        call.created_ticket_id = result.metadata["created_ticket_id"]
    db.commit()
    return result


def handle_lifecycle_event(db: Session, message: dict) -> None:
    """One event from Vapi's server-URL webhook (status-update,
    end-of-call-report, etc — see app/api/routes/voice.py). Everything not
    explicitly handled below is a no-op: we only track what the admin
    dashboard's call log actually needs (status/duration/transcript), not
    every Vapi event type.
    """
    call_id = (message.get("call") or {}).get("id")
    if not call_id:
        return
    call = db.query(Call).filter_by(vapi_call_id=call_id).one_or_none()
    if call is None:
        logger.warning("Vapi event for unknown call id %s", call_id)
        return

    event_type = message.get("type")
    if event_type == "status-update":
        status = message.get("status")
        if status == "ringing":
            call.status = CallStatus.RINGING
        elif status in ("in-progress", "forwarding"):
            call.status = CallStatus.IN_PROGRESS
        elif status == "ended":
            call.status = CallStatus.ENDED
            call.ended_at = utcnow()
    elif event_type == "end-of-call-report":
        call.status = CallStatus.FAILED if message.get("endedReason") == "error" else CallStatus.ENDED
        call.ended_reason = message.get("endedReason")
        call.ended_at = call.ended_at or utcnow()
        full_transcript = (message.get("artifact") or {}).get("transcript")
        if full_transcript:
            call.transcript = full_transcript

    db.commit()
