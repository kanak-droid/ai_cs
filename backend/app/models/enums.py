import enum


class TicketStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    ASSIGNED_TO_KAM = "assigned_to_kam"
    UNDER_REVIEW = "under_review"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# Statuses an admin may move a ticket to manually from the dashboard.
# SUBMITTED and ASSIGNED_TO_KAM are only ever set automatically on ticket creation.
ADMIN_SETTABLE_STATUSES = (
    TicketStatus.UNDER_REVIEW,
    TicketStatus.IN_PROGRESS,
    TicketStatus.RESOLVED,
    TicketStatus.CLOSED,
)
