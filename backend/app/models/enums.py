import enum


class TicketStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    ASSIGNED_TO_KAM = "assigned_to_kam"
    UNDER_REVIEW = "under_review"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# Statuses an admin may move a ticket to manually from the dashboard.
# SUBMITTED and ASSIGNED_TO_KAM are only ever set automatically on ticket
# creation. CLOSED is deliberately excluded (2026-08-20): the only manual
# terminal state is RESOLVED — closing is now always either the astrologer
# confirming it's fixed, or the 48h auto-close when they never respond (see
# ticket_service.record_satisfaction / _maybe_auto_close_stale), never a
# direct admin action. CLOSED itself stays a real, reachable TicketStatus
# value — just not one an admin can jump to manually.
ADMIN_SETTABLE_STATUSES = (
    TicketStatus.UNDER_REVIEW,
    TicketStatus.IN_PROGRESS,
    TicketStatus.RESOLVED,
)


class SessionResolution(str, enum.Enum):
    """How a ChatSession ended, for analytics — see app/models/chat_session.py."""

    BOT = "bot"
    ESCALATED = "escalated"


class AdminRole(str, enum.Enum):
    """KAM = personal point of contact, round-robin assigned to tickets
    (admin_mapping_client). CS = general support, sees everything in the
    dashboard but is never itself assigned as a ticket's KAM — see
    ticket_service.py's priority-aware routing (§7b in the approach doc).
    OTHERS = dashboard access for anyone who is neither — e.g. management —
    behaves like CS for ticket-routing purposes (never round-robin assigned)."""

    KAM = "kam"
    CS = "cs"
    OTHERS = "others"


class AdminAccessLevel(str, enum.Enum):
    """Dashboard privilege level — orthogonal to AdminRole (kam/cs), which is
    about ticket routing, not permissions. ADMIN can grant/manage other
    people's dashboard access (see auth_service.grant_access); NORMAL can
    only work tickets."""

    NORMAL = "normal"
    ADMIN = "admin"
