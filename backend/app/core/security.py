from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(frozen=True)
class AstrologerContext:
    """Identity resolved from a verified astrologer JWT. Never built from request bodies."""

    astrologer_id: int
    name: str
    language: str


@dataclass(frozen=True)
class AdminContext:
    """Identity resolved from a verified admin JWT."""

    admin_id: int
    email: str
    access_level: str


class InvalidTokenError(Exception):
    pass


def decode_admin_token(token: str) -> AdminContext:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("role") != "admin":
        raise InvalidTokenError("Not an admin token")

    try:
        return AdminContext(
            admin_id=int(payload["admin_id"]),
            email=str(payload["email"]),
            # Defaults to "normal" for tokens issued before access_level
            # existed, rather than treating them as malformed.
            access_level=str(payload.get("access_level", "normal")),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError("Malformed admin token payload") from exc


def issue_admin_token(admin_id: int, email: str, access_level: str) -> str:
    payload = {
        "admin_id": admin_id,
        "email": email,
        "role": "admin",
        "access_level": access_level,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.ADMIN_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
