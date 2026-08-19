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
    kam_performance: list[KamPerformance]
    weekly_ticket_trend: list[TicketPeriodCount]
    monthly_ticket_trend: list[TicketPeriodCount]
