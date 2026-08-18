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
