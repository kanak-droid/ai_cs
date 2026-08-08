from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.models.astrologer import Astrologer
from app.schemas.admin import AstrologerRead

router = APIRouter(tags=["admin"])


@router.get("/api/admin/astrologers", response_model=list[AstrologerRead])
def list_astrologers(
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AstrologerRead]:
    astrologers = db.scalars(select(Astrologer).order_by(Astrologer.name)).all()
    return [AstrologerRead.model_validate(a) for a in astrologers]
