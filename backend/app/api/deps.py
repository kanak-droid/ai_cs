from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import AdminContext, AstrologerContext, InvalidTokenError
from app.db.session import SessionLocal
from app.services import auth_service

_bearer_scheme = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_astrologer(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> AstrologerContext:
    try:
        return auth_service.verify_astrologer_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session"
        ) from exc


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> AdminContext:
    try:
        return auth_service.verify_admin_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired admin session"
        ) from exc
