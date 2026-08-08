from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import TicketStatus
from app.schemas.ticket import TicketRead


class AstrologerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    language: str
    photo_url: str | None = None
    assigned_admin_id: int | None = None


class AdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    slack_channel: str


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


class TicketQueueFilters(BaseModel):
    status: TicketStatus | None = None
    assigned_admin_id: int | None = None
