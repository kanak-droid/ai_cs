from pydantic import BaseModel


class CategoryCount(BaseModel):
    category: str
    count: int


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
