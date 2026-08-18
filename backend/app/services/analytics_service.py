"""Aggregates ChatSession + Ticket data for the admin analytics dashboard.

Read-only — nothing here writes anything. "Top issues" is computed from
ChatSession.category rather than Ticket.category, since a ChatSession exists
for both bot-resolved AND escalated issues (a ticket's category is a subset
of that, already reflected via the linked session) — this is what gives us
"how common is each kind of issue" across ALL conversations, not just the
ones that became tickets.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.integrations import queue_performance_client
from app.models.admin import Admin
from app.models.chat_session import ChatSession
from app.models.enums import SessionResolution, TicketStatus
from app.models.ticket import Ticket

_TERMINAL_STATUSES = (TicketStatus.RESOLVED, TicketStatus.CLOSED)


def _astrologer_ids_matching_priority(db: Session, priority: str | None) -> set[int] | None:
    """None means "no filter" — every astrologer. Otherwise the set of
    astrologer_ids whose CURRENT live-computed priority matches `priority`
    ("1".."5" or "unranked") — the same computation get_priority_ranking
    and ticket-queue sorting use, so this filter means the same thing
    everywhere else priority does.

    Scoped to astrologers who actually appear in a ChatSession or Ticket
    (the only ones analytics ever looks at), not every astrologer in the
    platform — bounded by real activity, not the full roster.
    """
    if not priority:
        return None
    target = None if priority == "unranked" else int(priority)

    candidate_ids = {
        astrologer_id
        for (astrologer_id,) in db.execute(
            select(ChatSession.astrologer_id).union(select(Ticket.astrologer_id))
        )
    }
    cache: dict[int, int | None] = {}
    matching = set()
    for astrologer_id in candidate_ids:
        if astrologer_id not in cache:
            cache[astrologer_id] = queue_performance_client.get_queue_performance(
                db, astrologer_id
            ).priority
        if cache[astrologer_id] == target:
            matching.add(astrologer_id)
    return matching


def _get_kam_performance(db: Session, astrologer_ids: set[int] | None) -> list[dict]:
    """Per-KAM/CS ticket workload — "assigned" checks both assigned_admin_id
    (KAM) and assigned_cs_id (CS), same generic-assignment convention as
    ticket_service.list_all_tickets' assigned_admin_id filter, since the
    same admin can be either depending on role.
    """
    admins = db.scalars(select(Admin).where(Admin.is_active.is_(True)).order_by(Admin.name)).all()
    results = []
    for admin in admins:
        conditions = [Ticket.assigned_admin_id == admin.id, Ticket.assigned_cs_id == admin.id]
        assigned_filter = or_(*conditions)
        base_query = db.query(Ticket).filter(assigned_filter)
        if astrologer_ids is not None:
            base_query = base_query.filter(Ticket.astrologer_id.in_(astrologer_ids))

        assigned_count = base_query.count()
        pending_count = base_query.filter(Ticket.status.not_in(_TERMINAL_STATUSES)).count()
        solved_count = base_query.filter(Ticket.status.in_(_TERMINAL_STATUSES)).count()
        avg_tat_hours = (
            base_query.filter(Ticket.resolved_at.isnot(None))
            .with_entities(func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at)) / 3600)
            .scalar()
        )
        results.append(
            {
                "admin_id": admin.id,
                "name": admin.name,
                "role": admin.role.value,
                "pending_count": pending_count,
                "assigned_count": assigned_count,
                "solved_count": solved_count,
                "avg_tat_hours": float(avg_tat_hours) if avg_tat_hours is not None else None,
            }
        )
    return results


def get_overview(db: Session, priority: str | None = None) -> dict:
    astrologer_ids = _astrologer_ids_matching_priority(db, priority)

    session_query = db.query(ChatSession)
    ticket_query = db.query(Ticket)
    if astrologer_ids is not None:
        session_query = session_query.filter(ChatSession.astrologer_id.in_(astrologer_ids))
        ticket_query = ticket_query.filter(Ticket.astrologer_id.in_(astrologer_ids))

    resolution_counts = dict(
        session_query.filter(ChatSession.resolved_by.isnot(None))
        .with_entities(ChatSession.resolved_by, func.count(ChatSession.id))
        .group_by(ChatSession.resolved_by)
        .all()
    )
    bot_resolved_count = resolution_counts.get(SessionResolution.BOT, 0)
    escalated_count = resolution_counts.get(SessionResolution.ESCALATED, 0)

    top_categories = (
        session_query.filter(ChatSession.category.isnot(None))
        .with_entities(ChatSession.category, func.count(ChatSession.id))
        .group_by(ChatSession.category)
        .order_by(func.count(ChatSession.id).desc())
        .limit(10)
        .all()
    )

    avg_bot_resolution_seconds = (
        session_query.filter(ChatSession.resolved_by == SessionResolution.BOT)
        .with_entities(func.avg(func.extract("epoch", ChatSession.resolved_at - ChatSession.started_at)))
        .scalar()
    )

    avg_ticket_resolution_hours = (
        ticket_query.filter(Ticket.resolved_at.isnot(None))
        .with_entities(func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at)) / 3600)
        .scalar()
    )

    satisfaction_counts = dict(
        ticket_query.filter(Ticket.satisfaction.isnot(None))
        .with_entities(Ticket.satisfaction, func.count(Ticket.id))
        .group_by(Ticket.satisfaction)
        .all()
    )

    rating_rows = (
        session_query.filter(ChatSession.rating.isnot(None))
        .with_entities(ChatSession.rating, func.count(ChatSession.id))
        .group_by(ChatSession.rating)
        .all()
    )
    avg_bot_rating = (
        session_query.filter(ChatSession.rating.isnot(None))
        .with_entities(func.avg(ChatSession.rating))
        .scalar()
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
        # Deliberately NOT filtered by astrologer_ids/priority — a KAM/CS's
        # overall workload numbers wouldn't make sense scoped to only one
        # priority tier's astrologers; this table is its own view.
        "kam_performance": _get_kam_performance(db, None),
    }
