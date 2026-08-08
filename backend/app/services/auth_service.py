from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    AdminContext,
    AstrologerContext,
    InvalidTokenError,
    decode_admin_token,
    decode_astrologer_token,
    issue_admin_token,
    verify_password,
)
from app.models.admin import Admin

__all__ = ["InvalidTokenError", "AstrologerContext", "AdminContext"]


def verify_astrologer_token(token: str) -> AstrologerContext:
    return decode_astrologer_token(token)


def verify_admin_token(token: str) -> AdminContext:
    return decode_admin_token(token)


def authenticate_admin(db: Session, email: str, password: str) -> Admin | None:
    admin = db.scalar(select(Admin).where(Admin.email == email, Admin.is_active.is_(True)))
    if admin is None or not verify_password(password, admin.password_hash):
        return None
    return admin


def login_admin(db: Session, email: str, password: str) -> tuple[Admin, str] | None:
    admin = authenticate_admin(db, email, password)
    if admin is None:
        return None
    token = issue_admin_token(admin.id, admin.email)
    return admin, token
