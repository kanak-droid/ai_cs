from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db, require_admin_access
from app.core.errors import NotFoundError
from app.core.security import AdminContext, hash_password
from app.models.admin import Admin
from app.schemas.admin import AdminCreateRequest, AdminRead, AdminUpdateRequest
from app.services import auth_service

router = APIRouter(tags=["admin"])


@router.get("/api/admin/admins", response_model=list[AdminRead])
def list_admins(
    include_inactive: bool = Query(default=False),
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AdminRead]:
    """Without include_inactive: just active admins, for the ticket queue's
    "assigned admin" filter dropdown — open to any logged-in admin. With it:
    everyone (incl. deactivated), for the Admins management page — that view
    is roster management, so it's restricted to ADMIN access level.
    """
    if include_inactive and admin.access_level != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    stmt = select(Admin).order_by(Admin.name)
    if not include_inactive:
        stmt = stmt.where(Admin.is_active.is_(True))
    admins = db.scalars(stmt).all()
    return [AdminRead.model_validate(a) for a in admins]


@router.post("/api/admin/admins", response_model=AdminRead, status_code=201)
def create_admin(
    body: AdminCreateRequest,
    admin: AdminContext = Depends(require_admin_access),
    db: Session = Depends(get_db),
) -> AdminRead:
    """Grants a new email dashboard access, or re-grants an existing one —
    only an ADMIN-access admin can hand out normal or admin access."""
    granted = auth_service.grant_access(
        db,
        email=body.email,
        name=body.name,
        role=body.role,
        access_level=body.access_level,
        languages=body.languages,
        slack_user_id=body.slack_user_id,
    )
    return AdminRead.model_validate(granted)


@router.patch("/api/admin/admins/{admin_id}", response_model=AdminRead)
def update_admin(
    admin_id: int,
    body: AdminUpdateRequest,
    admin: AdminContext = Depends(require_admin_access),
    db: Session = Depends(get_db),
) -> AdminRead:
    """Lets an ADMIN-access admin activate/deactivate a profile, mark it
    temporarily on leave, change its KAM/CS role, or change its access
    level — e.g. deactivating the placeholder seed admins once real KAMs/CS
    are onboarded, without deleting their ticket history. Changing
    access_level resets the target's password to the new tier's shared
    password, same as grant_access.

    is_temporarily_inactive vs is_active: on-leave (is_temporarily_inactive)
    is a short, reversible break — is_active stays True the whole time, so
    they keep appearing everywhere an active admin does (admin lists, the
    ticket queue's assigned-admin lookup) and their existing tickets keep
    showing correctly. It only excludes them from NEW round-robin
    assignment. is_active=False is the permanent case.
    """
    target = db.get(Admin, admin_id)
    if target is None:
        raise NotFoundError(f"Admin {admin_id} not found")

    if body.role is not None:
        target.role = body.role
    if body.access_level is not None:
        target.access_level = body.access_level
        target.password_hash = hash_password(auth_service.password_for_access_level(body.access_level))
    if body.languages is not None:
        target.languages = body.languages
    if body.is_active is not None:
        target.is_active = body.is_active
    if body.is_temporarily_inactive is not None:
        target.is_temporarily_inactive = body.is_temporarily_inactive
    if body.slack_user_id is not None:
        target.slack_user_id = body.slack_user_id

    db.commit()
    db.refresh(target)
    return AdminRead.model_validate(target)
