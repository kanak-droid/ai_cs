from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.schemas.call_log import CallLogDetailRead, CallLogSummaryRead
from app.services import call_log_service, call_service

router = APIRouter(tags=["admin"])


class TriggerFeedbackCallRequest(BaseModel):
    astrologer_id: int


class TriggerFeedbackCallResponse(BaseModel):
    call_id: int
    status: str


@router.post(
    "/api/admin/feedback-calls/trigger",
    response_model=TriggerFeedbackCallResponse,
)
def trigger_feedback_call(
    body: TriggerFeedbackCallRequest,
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> TriggerFeedbackCallResponse:
    call = call_service.request_feedback_call(db, body.astrologer_id)
    return TriggerFeedbackCallResponse(call_id=call.id, status=call.status.value)


@router.get(
    "/api/admin/feedback-calls",
    response_model=list[CallLogSummaryRead],
)
def list_feedback_calls(
    resolution_status: str | None = None,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    astrologer_search: str | None = Query(None, alias="astrologer"),
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[CallLogSummaryRead]:
    return call_log_service.list_call_logs(
        db,
        resolution_status=resolution_status,
        date_from=date_from,
        date_to=date_to,
        astrologer_search=astrologer_search,
        triggered_by="feedback_call",
    )


@router.get(
    "/api/admin/feedback-calls/{call_id}",
    response_model=CallLogDetailRead,
)
def get_feedback_call(
    call_id: int,
    admin: AdminContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> CallLogDetailRead:
    return call_log_service.get_call_log(db, call_id)
