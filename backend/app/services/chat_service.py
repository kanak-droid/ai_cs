import re

from sqlalchemy.orm import Session

from app.agent.client import AgentClient, get_agent_client
from app.agent.context import SessionContext
from app.agent.orchestrator import ChatTurnResult, HistoryTurn, run_chat_turn
from app.core.security import AstrologerContext
from app.schemas.chat import ChatHistoryTurn
from app.services import chat_session_service

# Matches the marker chat-app appends to a message when the astrologer attaches
# a photo/video (see chat-app's ChatPage.tsx) — used to find the most recently
# shared attachment across the whole conversation, not just the current message.
_ATTACHMENT_URL_PATTERN = re.compile(r"\[Uploaded attachment URL: (.+?)\]")


def _find_last_attachment_url(message: str, history: list[ChatHistoryTurn]) -> str | None:
    match = _ATTACHMENT_URL_PATTERN.search(message)
    if match:
        return match.group(1)
    for turn in reversed(history):
        match = _ATTACHMENT_URL_PATTERN.search(turn.text)
        if match:
            return match.group(1)
    return None


def handle_chat_turn(
    db: Session,
    astrologer: AstrologerContext,
    message: str,
    *,
    history: list[ChatHistoryTurn] | None = None,
    session_id: str | None = None,
    client: AgentClient | None = None,
) -> ChatTurnResult:
    history = history or []
    chat_session_service.get_or_create_session(db, session_id, astrologer.astrologer_id)
    ctx = SessionContext(
        astrologer_id=astrologer.astrologer_id,
        name=astrologer.name,
        language=astrologer.language,
        db=db,
        last_attachment_url=_find_last_attachment_url(message, history),
        session_id=session_id,
        has_prior_reply=any(turn.role == "assistant" for turn in history),
    )
    agent_history = [HistoryTurn(role=turn.role, text=turn.text) for turn in history]
    result = run_chat_turn(client or get_agent_client(), ctx, message, history=agent_history)
    db.commit()
    return result
