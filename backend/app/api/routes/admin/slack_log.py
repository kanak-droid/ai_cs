from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.models.slack_log import SlackLog
from app.schemas.admin import SlackLogRead

router = APIRouter(tags=["admin"])


@router.get("/api/admin/slack-log", response_model=list[SlackLogRead])
def list_slack_log(
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[SlackLogRead]:
    entries = db.scalars(select(SlackLog).order_by(SlackLog.sent_at.desc())).all()
    return [SlackLogRead.model_validate(e) for e in entries]
