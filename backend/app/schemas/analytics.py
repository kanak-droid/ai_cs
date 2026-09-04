from datetime import datetime

from pydantic import BaseModel


class CategoryCount(BaseModel):
    category: str
    count: int


class KamPerformance(BaseModel):
    admin_id: int
    name: str
    role: str
    pending_count: int
    assigned_count: int
    solved_count: int
    # Only meaningful for CS rows — tickets they escalated to the KAM,
    # already excluded from solved_count above. Always 0 for KAM rows.
    escalated_to_kam_count: int
    # Average hours from ticket creation to resolution, for tickets they
    # solved — None if they haven't solved any yet.
    avg_tat_hours: float | None = None


class TicketPeriodCount(BaseModel):
    # ISO date of the bucket's start (e.g. the Monday of that week, or the
    # 1st of that month) — a plain string rather than a richer period type
    # since the frontend only ever uses it as a chart axis label.
    period: str
    created_count: int
    resolved_count: int


class AnalyticsOverview(BaseModel):
    bot_resolved_count: int
    escalated_count: int
    top_categories: list[CategoryCount]
    avg_bot_resolution_seconds: float | None = None
    avg_ticket_resolution_hours: float | None = None
    satisfied_count: int
    unsatisfied_count: int
    avg_bot_rating: float | None = None
    rating_distribution: dict[str, int]
    # The astrologer's 1-5 star rating of a ticket's resolution — distinct
    # from avg_bot_rating/rating_distribution above, which are the bot
    # CONVERSATION rating (ChatSession.rating), not tied to any ticket.
    avg_ticket_rating: float | None = None
    ticket_rating_distribution: dict[str, int]
    total_calls: int
    avg_call_duration_seconds: float | None = None
    call_resolution_counts: dict[str, int]
    calls_with_ticket: int
    kam_performance: list[KamPerformance]
    weekly_ticket_trend: list[TicketPeriodCount]
    monthly_ticket_trend: list[TicketPeriodCount]


class TicketRatingEntry(BaseModel):
    ticket_id: int
    astrologer_name: str
    category: str
    rating: int
    reasons: list[str]
    comment: str | None
    rated_at: datetime
