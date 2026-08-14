"""Aggregates ChatSession + Ticket data for the admin analytics dashboard.

Read-only — nothing here writes anything. "Top issues" is computed from
ChatSession.category rather than Ticket.category, since a ChatSession exists
for both bot-resolved AND escalated issues (a ticket's category is a subset
of that, already reflected via the linked session) — this is what gives us
"how common is each kind of issue" across ALL conversations, not just the
ones that became tickets.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.models.enums import SessionResolution
from app.models.ticket import Ticket


def get_overview(db: Session) -> dict:
    resolution_counts = dict(
        db.query(ChatSession.resolved_by, func.count(ChatSession.id))
        .filter(ChatSession.resolved_by.isnot(None))
        .group_by(ChatSession.resolved_by)
        .all()
    )
    bot_resolved_count = resolution_counts.get(SessionResolution.BOT, 0)
    escalated_count = resolution_counts.get(SessionResolution.ESCALATED, 0)

    top_categories = (
        db.query(ChatSession.category, func.count(ChatSession.id))
        .filter(ChatSession.category.isnot(None))
        .group_by(ChatSession.category)
        .order_by(func.count(ChatSession.id).desc())
        .limit(10)
        .all()
    )

    avg_bot_resolution_seconds = (
        db.query(func.avg(func.extract("epoch", ChatSession.resolved_at - ChatSession.started_at)))
        .filter(ChatSession.resolved_by == SessionResolution.BOT)
        .scalar()
    )

    avg_ticket_resolution_hours = (
        db.query(func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at)) / 3600)
        .filter(Ticket.resolved_at.isnot(None))
        .scalar()
    )

    satisfaction_counts = dict(
        db.query(Ticket.satisfaction, func.count(Ticket.id))
        .filter(Ticket.satisfaction.isnot(None))
        .group_by(Ticket.satisfaction)
        .all()
    )

    rating_rows = (
        db.query(ChatSession.rating, func.count(ChatSession.id))
        .filter(ChatSession.rating.isnot(None))
        .group_by(ChatSession.rating)
        .all()
    )
    avg_bot_rating = (
        db.query(func.avg(ChatSession.rating)).filter(ChatSession.rating.isnot(None)).scalar()
    )

    return {
        "bot_resolved_count": bot_resolved_count,
        "escalated_count": escalated_count,
        "top_categories": [{"category": c, "count": n} for c, n in top_categories],
        "avg_bot_resolution_seconds": (
            float(avg_bot_resolution_seconds) if avg_bot_resolution_seconds is not None else None
        ),
        "avg_ticket_resolution_hours": (
            float(avg_ticket_resolution_hours) if avg_ticket_resolution_hours is not None else None
        ),
        "satisfied_count": satisfaction_counts.get("satisfied", 0),
        "unsatisfied_count": satisfaction_counts.get("unsatisfied", 0),
        "avg_bot_rating": float(avg_bot_rating) if avg_bot_rating is not None else None,
        "rating_distribution": {str(rating): count for rating, count in rating_rows},
    }
