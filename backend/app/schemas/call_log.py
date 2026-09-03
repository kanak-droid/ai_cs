from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import CallStatus


class CallLogSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    astrologer_id: int
    astrologer_name: str
    priority: int | None = None
    phone_number: str
    triggered_by: str
    ticket_id: int | None = None
    created_ticket_id: int | None = None
    status: CallStatus
    ended_reason: str | None = None
    resolution_status: str | None = None
    support_summary: str | None = None
    created_at: datetime
    ended_at: datetime | None = None


class CallLogDetailRead(CallLogSummaryRead):
    transcript: str | None = None
    suggested_solution: str | None = None
    next_action: str | None = None
    actions_taken: list[dict] | None = None
