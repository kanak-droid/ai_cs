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
    """

    astrologer_id: int
    name: str
    language: str
    db: Session
    last_attachment_url: str | None = None
    session_id: str | None = None
