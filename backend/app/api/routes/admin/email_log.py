from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.models.email_log import EmailLog
from app.schemas.admin import EmailLogRead

router = APIRouter(tags=["admin"])


@router.get("/api/admin/email-log", response_model=list[EmailLogRead])
def list_email_log(
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[EmailLogRead]:
    entries = db.scalars(select(EmailLog).order_by(EmailLog.sent_at.desc())).all()
    return [EmailLogRead.model_validate(e) for e in entries]
