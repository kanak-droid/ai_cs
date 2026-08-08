from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import TicketStatus


class TicketStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: TicketStatus
    changed_at: datetime
    changed_by: str
    note: str | None = None


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    astrologer_id: int
    category: str
    sub_category: str
    description: str
    description_en: str
    preferred_language: str
    attachment_url: str | None = None
    assigned_admin_id: int | None = None
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    history: list[TicketStatusHistoryRead] = []


class TicketStatusUpdateRequest(BaseModel):
    status: TicketStatus
    note: str | None = None
