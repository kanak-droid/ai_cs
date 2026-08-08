from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.models.admin import Admin
from app.schemas.admin import AdminRead

router = APIRouter(tags=["admin"])


@router.get("/api/admin/admins", response_model=list[AdminRead])
def list_admins(
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AdminRead]:
    """Used by the dashboard's "assigned admin" filter dropdown."""
    admins = db.scalars(select(Admin).where(Admin.is_active.is_(True)).order_by(Admin.name)).all()
    return [AdminRead.model_validate(a) for a in admins]
