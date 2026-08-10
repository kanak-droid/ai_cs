from sqlalchemy.orm import Session

from app.agent.client import AgentClient, get_agent_client
from app.agent.context import SessionContext
from app.agent.orchestrator import ChatTurnResult, HistoryTurn, run_chat_turn
from app.core.security import AstrologerContext
from app.schemas.chat import ChatHistoryTurn


def handle_chat_turn(
    db: Session,
    astrologer: AstrologerContext,
    message: str,
    *,
    history: list[ChatHistoryTurn] | None = None,
    client: AgentClient | None = None,
) -> ChatTurnResult:
    ctx = SessionContext(
        astrologer_id=astrologer.astrologer_id,
        name=astrologer.name,
        language=astrologer.language,
        db=db,
    )
    agent_history = [HistoryTurn(role=turn.role, text=turn.text) for turn in (history or [])]
    return run_chat_turn(client or get_agent_client(), ctx, message, history=agent_history)
