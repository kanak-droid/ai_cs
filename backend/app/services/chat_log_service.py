"""Chat transcripts for the admin dashboard's "Chatbot" section (added
2026-08-18) — lets a KAM/CS see what astrologers are actually asking the
bot, sorted by priority same as the ticket queue, split into still-going
(active) vs concluded (resolved by the bot or escalated to a ticket)
sections on the frontend, same pattern as the ticket queue's active/closed
split.

Sessions from before this shipped have no ChatMessage rows at all — message
persistence didn't exist yet — so they show up with an empty transcript,
not an error; only ChatSession's own resolution metadata is available for
those.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import NotFoundError
from app.integrations import queue_performance_client
from app.models.chat_session import ChatSession


def _attach_display_fields(db: Session, sessions: list[ChatSession]) -> None:
    cache: dict[int, int | None] = {}
    for session in sessions:
        astrologer_id = session.astrologer_id
        if astrologer_id not in cache:
            cache[astrologer_id] = queue_performance_client.get_queue_performance(
                db, astrologer_id
            ).priority
        session.priority = cache[astrologer_id]
        session.astrologer_name = session.astrologer.name


def list_chat_sessions(db: Session) -> list[ChatSession]:
    sessions = list(
        db.scalars(select(ChatSession).options(joinedload(ChatSession.astrologer))).unique()
    )
    sessions.sort(key=lambda s: queue_performance_client.priority_sort_key(db, s.astrologer_id))
    _attach_display_fields(db, sessions)
    return sessions


def get_chat_session(db: Session, chat_session_id: int) -> ChatSession:
    session = db.scalars(
        select(ChatSession)
        .where(ChatSession.id == chat_session_id)
        .options(joinedload(ChatSession.astrologer), selectinload(ChatSession.messages))
    ).one_or_none()
    if session is None:
        raise NotFoundError(f"Chat session {chat_session_id} not found")
    _attach_display_fields(db, [session])
    return session
