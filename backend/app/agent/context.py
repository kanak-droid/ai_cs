from dataclasses import dataclass

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class SessionContext:
    """Everything a tool handler is allowed to know about who's asking.

    astrologer_id here comes from the verified JWT (see app.core.security),
    never from a request body or from anything the model supplies — this is the
    only astrologer_id a tool handler should ever use.
    """

    astrologer_id: int
    name: str
    language: str
    db: Session
