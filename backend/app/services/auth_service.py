from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    AdminContext,
    AstrologerContext,
    InvalidTokenError,
    decode_admin_token,
    hash_password,
    issue_admin_token,
    verify_password,
)
from app.models.admin import Admin
from app.models.astrologer import Astrologer
from app.models.enums import AdminAccessLevel, AdminRole

__all__ = ["InvalidTokenError", "AstrologerContext", "AdminContext"]


def resolve_astrologer_by_user_id(db: Session, user_id: int) -> AstrologerContext:
    """The webview URL's identity, verified. There's no signature to check —
    the main AstroLokal app hands off a plain user_id, so the only "proof" we
    have is that Astrologer.user_id matches a real, linked astrologer."""
    astrologer = db.scalar(select(Astrologer).where(Astrologer.user_id == user_id))
    if astrologer is None:
        raise InvalidTokenError("No astrologer is linked to this user_id")
    return AstrologerContext(
        astrologer_id=astrologer.id, name=astrologer.name, language=astrologer.language
    )


def verify_astrologer_session(db: Session, raw_user_id: str) -> AstrologerContext:
    try:
        user_id = int(raw_user_id)
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError("user_id must be an integer") from exc
    return resolve_astrologer_by_user_id(db, user_id)


def verify_admin_token(token: str) -> AdminContext:
    return decode_admin_token(token)


def authenticate_admin(db: Session, email: str, password: str) -> Admin | None:
    admin = db.scalar(select(Admin).where(Admin.email == email, Admin.is_active.is_(True)))
    if admin is None or admin.password_hash is None:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin


def login_admin(db: Session, email: str, password: str) -> tuple[Admin, str] | None:
    # No domain restriction — any email can log in, as long as an existing
    # admin granted it access (see grant_access). That row's existence IS
    # the access control.
    admin = authenticate_admin(db, email, password)
    if admin is None:
        return None
    token = issue_admin_token(admin.id, admin.email, admin.access_level.value)
    return admin, token


def password_for_access_level(access_level: AdminAccessLevel) -> str:
    return (
        settings.ADMIN_ACCESS_PASSWORD
        if access_level == AdminAccessLevel.ADMIN
        else settings.NORMAL_ACCESS_PASSWORD
    )


def grant_access(
    db: Session,
    *,
    email: str,
    name: str,
    role: AdminRole,
    access_level: AdminAccessLevel,
    languages: list[str] | None = None,
) -> Admin:
    """Create or update an admin's dashboard access — the only way an email
    ever gets a working login; there is no self-service signup and no
    domain restriction (any email works, as long as an existing admin
    grants it).

    Password is always the fixed, shared password for the assigned
    access_level (see password_for_access_level) and resets automatically
    whenever access_level changes, so "become an admin" and "get the admin
    password" are the same action.

    `languages` matters for CS admins — see cs_assignment_client — but is
    accepted for any role in case a KAM/other also needs it recorded.
    """
    admin = db.scalar(select(Admin).where(Admin.email == email))
    if admin is None:
        admin = Admin(name=name, email=email, role=role, access_level=access_level)
        db.add(admin)
    else:
        admin.name = name
        admin.role = role
        admin.access_level = access_level
    if languages is not None:
        admin.languages = languages
    admin.password_hash = hash_password(password_for_access_level(access_level))
    admin.is_active = True
    db.commit()
    db.refresh(admin)
    return admin
