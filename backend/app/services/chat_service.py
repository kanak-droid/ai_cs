from sqlalchemy.orm import Session

from app.agent.client import AgentClient, get_agent_client
from app.agent.context import SessionContext
from app.agent.orchestrator import ChatTurnResult, run_chat_turn
from app.core.security import AstrologerContext


def handle_chat_turn(
    db: Session,
    astrologer: AstrologerContext,
    message: str,
    *,
    client: AgentClient | None = None,
) -> ChatTurnResult:
    ctx = SessionContext(
        astrologer_id=astrologer.astrologer_id,
        name=astrologer.name,
        language=astrologer.language,
        db=db,
    )
    return run_chat_turn(client or get_agent_client(), ctx, message)
