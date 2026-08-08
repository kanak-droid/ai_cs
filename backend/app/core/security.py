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


class InvalidTokenError(Exception):
    pass


def decode_astrologer_token(token: str) -> AstrologerContext:
    """Verify a token issued by the main AstroLokal backend (shared HS256 secret).

    This backend only ever verifies these tokens, never issues them, except via
    the local-dev `scripts/mint_dev_token.py` helper.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.ASTROLOGER_TOKEN_ALGORITHM]
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if "role" in payload:
        # Astrologer tokens never carry a role claim — this is an admin token
        # presented in the wrong place.
        raise InvalidTokenError("Not an astrologer token")

    try:
        return AstrologerContext(
            astrologer_id=int(payload["astrologer_id"]),
            name=str(payload["name"]),
            language=str(payload.get("language", "English")),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError("Malformed astrologer token payload") from exc


def decode_admin_token(token: str) -> AdminContext:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("role") != "admin":
        raise InvalidTokenError("Not an admin token")

    try:
        return AdminContext(admin_id=int(payload["admin_id"]), email=str(payload["email"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError("Malformed admin token payload") from exc


def issue_admin_token(admin_id: int, email: str) -> str:
    payload = {
        "admin_id": admin_id,
        "email": email,
        "role": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.ADMIN_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
