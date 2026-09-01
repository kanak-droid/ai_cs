from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TicketStatus


class TicketStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: TicketStatus
    changed_at: datetime
    changed_by: str
    note: str | None = None
    is_status_change: bool = True


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
    assigned_cs_id: int | None = None
    kam_notified: bool
    cs_notified: bool
    status: TicketStatus
    resolved_at: datetime | None = None
    satisfaction: str | None = None
    rating: int | None = None
    rating_reasons: list[str] | None = None
    rating_comment: str | None = None
    rated_at: datetime | None = None
    escalated_to_kam: bool
    escalated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    history: list[TicketStatusHistoryRead] = []


class TicketStatusUpdateRequest(BaseModel):
    status: TicketStatus
    note: str | None = None


class TicketRatingRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    reasons: list[str] = Field(default_factory=list)
    comment: str | None = None


class TicketReassignRequest(BaseModel):
    role: str  # "kam" | "cs"
    admin_id: int
    note: str | None = None


class TicketBulkReassignRequest(BaseModel):
    ticket_ids: list[int]
    role: str  # "kam" | "cs"
    admin_id: int
    note: str | None = None


class TicketBulkReassignResult(BaseModel):
    ticket_id: int
    ok: bool
    error: str | None = None


class TicketBulkReassignResponse(BaseModel):
    results: list[TicketBulkReassignResult]


class TicketEscalateRequest(BaseModel):
    # Mandatory — a CS escalating to a KAM must explain why (see
    # ticket_service.escalate_to_kam).
    note: str


class AttachmentPreviewResponse(BaseModel):
    # A short-lived, signed URL — safe to load directly in an <img>/<a
    # href download>, unlike the ticket's raw attachment_url (see
    # object_storage.generate_preview_url).
    preview_url: str
