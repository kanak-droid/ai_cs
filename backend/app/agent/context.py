from dataclasses import dataclass

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class SessionContext:
    """Everything a tool handler is allowed to know about who's asking.

    astrologer_id here comes from the verified JWT (see app.core.security),
    never from a request body or from anything the model supplies — this is the
    only astrologer_id a tool handler should ever use.

    last_attachment_url is the most recent photo/video URL found anywhere in
    this conversation (current message + history) — see chat_service — so a
    ticket raised later in the same chat can attach it automatically instead
    of asking the astrologer to resend it.

    session_id identifies this webview visit for analytics only (see
    app.services.chat_session_service) — optional, and never used for
    anything astrologer/ticket flows depend on.

    has_prior_reply is True once this conversation already has at least one
    assistant turn behind it (see chat_service) — a purely mechanical fact
    about the conversation's shape, computed from the client-supplied
    history, not something the model reports about itself. Used to gate
    premature escalation (e.g. a non-VIP "no_visibility" ticket — see
    tool_registry) deterministically in code: the prompt alone can't be
    trusted to reliably wait for a first round of self-help advice before
    raising a ticket, since instruction-following isn't 100% reliable
    (observed live, 2026-08-16 — see docs/chatbot-approach.md §7d).
    """

    astrologer_id: int
    name: str
    language: str
    db: Session
    last_attachment_url: str | None = None
    session_id: str | None = None
    has_prior_reply: bool = False
