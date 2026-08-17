from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import AdminAccessLevel, AdminRole, TicketStatus
from app.schemas.ticket import TicketRead


class AstrologerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    language: str
    photo_url: str | None = None
    assigned_admin_id: int | None = None
    # Join key into the ops team's Google Sheets — None for astrologers ops
    # hasn't linked to a real expert yet (mocked payout/KYC/priority data).
    expert_id: int | None = None
    # Transient — set by ticket_service.attach_astrologer_priority, not a
    # real column (see that function's docstring). None only if the caller
    # forgot to attach it.
    priority: int | None = None


class AdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    slack_channel: str
    slack_user_id: str | None = None
    role: AdminRole
    access_level: AdminAccessLevel
    languages: list[str]
    is_active: bool


class AdminCreateRequest(BaseModel):
    name: str
    email: EmailStr
    role: AdminRole
    access_level: AdminAccessLevel = AdminAccessLevel.NORMAL
    languages: list[str] = []
    slack_user_id: str | None = None


class AdminUpdateRequest(BaseModel):
    role: AdminRole | None = None
    access_level: AdminAccessLevel | None = None
    languages: list[str] | None = None
    is_active: bool | None = None
    slack_user_id: str | None = None


class AdminTicketRead(TicketRead):
    astrologer: AstrologerRead


class SlackLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: str
    message: str
    ticket_id: int | None = None
    sent_at: datetime
    mock: bool


class EmailLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    to_email: str
    subject: str
    body: str
    sent_at: datetime
    mock: bool


class TicketQueueFilters(BaseModel):
    status: TicketStatus | None = None
    assigned_admin_id: int | None = None
