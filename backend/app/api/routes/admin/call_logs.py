from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.schemas.call_log import CallLogDetailRead, CallLogSummaryRead
from app.services import call_log_service

router = APIRouter(tags=["admin"])


@router.get("/api/admin/call-logs", response_model=list[CallLogSummaryRead])
def list_call_logs(
    resolution_status: str | None = Query(default=None),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    astrologer: str | None = Query(default=None),
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[CallLogSummaryRead]:
    calls = call_log_service.list_call_logs(
        db,
        resolution_status=resolution_status,
        date_from=date_from,
        date_to=date_to,
        astrologer_search=astrologer,
    )
    return [CallLogSummaryRead.model_validate(c) for c in calls]


@router.get("/api/admin/call-logs/{call_id}", response_model=CallLogDetailRead)
def get_call_log(
    call_id: int,
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> CallLogDetailRead:
    call = call_log_service.get_call_log(db, call_id)
    return CallLogDetailRead.model_validate(call)
