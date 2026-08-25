"""Analytics-only logging of chat resolutions — see app/models/chat_session.py.

Nothing here is load-bearing for the astrologer/admin ticket flows; every
function is best-effort and safe to no-op when session_id is absent (older
clients, or direct executor calls in tests) so a logging gap never breaks chat.
"""

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.enums import SessionResolution


def get_or_create_session(db: Session, session_id: str | None, astrologer_id: int) -> ChatSession | None:
    if not session_id:
        return None
    session = db.query(ChatSession).filter_by(session_id=session_id).one_or_none()
    if session is None:
        session = ChatSession(session_id=session_id, astrologer_id=astrologer_id)
        db.add(session)
        db.flush()
    return session


def record_message(db: Session, session: ChatSession | None, *, role: str, text: str) -> None:
    """Persists one turn's raw text for the admin dashboard's chat-log view
    (added 2026-08-18) — before this, no message content was ever stored,
    only ChatSession's resolution metadata. Best-effort/no-op without a
    session, same as everything else in this file, so a logging gap never
    breaks the actual chat.
    """
    if session is None:
        return
    db.add(ChatMessage(session_id=session.id, role=role, text=text))
    db.flush()


def mark_resolved_by_bot(
    db: Session, session_id: str | None, *, category: str, sub_category: str
) -> None:
    if not session_id:
        return
    session = db.query(ChatSession).filter_by(session_id=session_id).one_or_none()
    if session is None:
        return
    session.category = category
    session.sub_category = sub_category
    session.resolved_by = SessionResolution.BOT
    session.resolved_at = utcnow()
    db.flush()


def get_transcript_text(db: Session, session_id: str | None) -> str | None:
    """Formats a session's full persisted message history into readable
    text — e.g. for a Zoho ticket comment carrying the complete astrologer/
    bot conversation, not just the AI's short one-line description. None
    if there's no session_id, no matching session, or no persisted
    messages (older sessions predate ChatMessage — see its docstring).
    """
    if not session_id:
        return None
    session = db.query(ChatSession).filter_by(session_id=session_id).one_or_none()
    if session is None or not session.messages:
        return None
    role_label = {"astrologer": "Astrologer", "assistant": "Assistant"}
    return "\n\n".join(f"{role_label.get(m.role, m.role)}: {m.text}" for m in session.messages)


def mark_escalated(db: Session, session_id: str | None, *, ticket_id: int) -> None:
    if not session_id:
        return
    session = db.query(ChatSession).filter_by(session_id=session_id).one_or_none()
    if session is None:
        return
    session.resolved_by = SessionResolution.ESCALATED
    session.ticket_id = ticket_id
    session.resolved_at = utcnow()
    db.flush()


def record_feedback(
    db: Session,
    session_id: str,
    astrologer_id: int,
    *,
    rating: int,
    reasons: list[str] | None = None,
    comment: str | None,
) -> ChatSession | None:
    session = (
        db.query(ChatSession)
        .filter_by(session_id=session_id, astrologer_id=astrologer_id)
        .one_or_none()
    )
    if session is None:
        return None
    session.rating = rating
    session.feedback_reasons = reasons
    session.feedback_text = comment
    db.commit()
    db.refresh(session)
    return session
