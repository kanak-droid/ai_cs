"""Aggregates ChatSession + Ticket data for the admin analytics dashboard.

Read-only — nothing here writes anything. "Top issues" is computed from
ChatSession.category rather than Ticket.category, since a ChatSession exists
for both bot-resolved AND escalated issues (a ticket's category is a subset
of that, already reflected via the linked session) — this is what gives us
"how common is each kind of issue" across ALL conversations, not just the
ones that became tickets.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.integrations import queue_performance_client
from app.models.admin import Admin
from app.models.chat_session import ChatSession
from app.models.enums import AdminRole, SessionResolution, TicketStatus
from app.models.ticket import Ticket

_TERMINAL_STATUSES = (TicketStatus.RESOLVED, TicketStatus.CLOSED)
# Default lookback for the trend charts when no explicit date range is
# given — enough to be useful without silently rendering years of tiny
# buckets the first time an admin opens the page.
_DEFAULT_WEEKLY_TREND_SPAN = timedelta(weeks=12)
_DEFAULT_MONTHLY_TREND_SPAN = timedelta(days=365)


def _day_start(d: date) -> datetime:
    return datetime.combine(d, time.min)


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


def _get_kam_performance(
    db: Session,
    astrologer_ids: set[int] | None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    """Per-KAM/CS ticket workload — "assigned" checks both assigned_admin_id
    (KAM) and assigned_cs_id (CS), same generic-assignment convention as
    ticket_service.list_all_tickets' assigned_admin_id filter, since the
    same admin can be either depending on role.

    date_from/date_to scope this to tickets *raised* in that window (same
    field/semantics as the rest of get_overview) — unlike the priority
    filter below, which this table deliberately ignores, a date range is
    exactly the kind of "how did this KAM do last month" question this
    table exists to answer, so it applies here too.
    """
    admins = db.scalars(select(Admin).where(Admin.is_active.is_(True)).order_by(Admin.name)).all()
    results = []
    for admin in admins:
        conditions = [Ticket.assigned_admin_id == admin.id, Ticket.assigned_cs_id == admin.id]
        assigned_filter = or_(*conditions)
        base_query = db.query(Ticket).filter(assigned_filter)
        if astrologer_ids is not None:
            base_query = base_query.filter(Ticket.astrologer_id.in_(astrologer_ids))
        if date_from is not None:
            base_query = base_query.filter(Ticket.created_at >= _day_start(date_from))
        if date_to is not None:
            base_query = base_query.filter(Ticket.created_at < _day_start(date_to + timedelta(days=1)))

        assigned_count = base_query.count()
        pending_count = base_query.filter(Ticket.status.not_in(_TERMINAL_STATUSES)).count()
        # A ticket a CS escalated to the KAM was resolved BY THE KAM, not
        # this CS — exclude it from the CS's own "solved" tally even though
        # assigned_cs_id never changes on escalation (see
        # ticket_service.escalate_to_kam). Doesn't apply to KAM rows: a KAM
        # resolving an escalated ticket legitimately counts it.
        solved_query = base_query.filter(Ticket.status.in_(_TERMINAL_STATUSES))
        escalated_count = 0
        if admin.role == AdminRole.CS:
            escalated_count = base_query.filter(Ticket.escalated_to_kam.is_(True)).count()
            solved_query = solved_query.filter(Ticket.escalated_to_kam.is_(False))
        solved_count = solved_query.count()
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
                # Only meaningful for CS rows — always 0 for KAM (see above).
                "escalated_to_kam_count": escalated_count,
                "avg_tat_hours": float(avg_tat_hours) if avg_tat_hours is not None else None,
            }
        )
    return results


def _ticket_period_trend(
    db: Session, *, bucket: str, date_from: date | None, date_to: date | None
) -> list[dict]:
    """Ticket volume over time, bucketed by week or month — created vs
    resolved counts per period, so an admin can see load and throughput
    trending rather than just current totals. Deliberately independent of
    the priority filter (a volume trend mixing tiers is the point of a
    report like this); date_from/date_to bound which buckets appear, same
    as everywhere else in this module. Falls back to a fixed lookback
    window when neither is given, so this never silently renders years of
    tiny buckets on first load.
    """
    default_span = _DEFAULT_WEEKLY_TREND_SPAN if bucket == "week" else _DEFAULT_MONTHLY_TREND_SPAN
    range_start = date_from or (date.today() - default_span)
    range_end = date_to or date.today()
    start_dt = _day_start(range_start)
    end_dt = _day_start(range_end + timedelta(days=1))

    created_rows = dict(
        db.query(func.date_trunc(bucket, Ticket.created_at), func.count(Ticket.id))
        .filter(Ticket.created_at >= start_dt, Ticket.created_at < end_dt)
        .group_by(func.date_trunc(bucket, Ticket.created_at))
        .all()
    )
    resolved_rows = dict(
        db.query(func.date_trunc(bucket, Ticket.resolved_at), func.count(Ticket.id))
        .filter(
            Ticket.resolved_at.isnot(None),
            Ticket.resolved_at >= start_dt,
            Ticket.resolved_at < end_dt,
        )
        .group_by(func.date_trunc(bucket, Ticket.resolved_at))
        .all()
    )
    periods = sorted(set(created_rows) | set(resolved_rows))
    return [
        {
            "period": period.date().isoformat(),
            "created_count": created_rows.get(period, 0),
            "resolved_count": resolved_rows.get(period, 0),
        }
        for period in periods
    ]


def get_overview(
    db: Session,
    *,
    priority: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    astrologer_ids = _astrologer_ids_matching_priority(db, priority)

    session_query = db.query(ChatSession)
    ticket_query = db.query(Ticket)
    if astrologer_ids is not None:
        session_query = session_query.filter(ChatSession.astrologer_id.in_(astrologer_ids))
        ticket_query = ticket_query.filter(Ticket.astrologer_id.in_(astrologer_ids))
    # ChatSession.started_at / Ticket.created_at — "when this began", same
    # field the rest of this module already keys off of (e.g. TAT below is
    # always measured from created_at, never resolved_at).
    if date_from is not None:
        session_query = session_query.filter(ChatSession.started_at >= _day_start(date_from))
        ticket_query = ticket_query.filter(Ticket.created_at >= _day_start(date_from))
    if date_to is not None:
        end_dt = _day_start(date_to + timedelta(days=1))
        session_query = session_query.filter(ChatSession.started_at < end_dt)
        ticket_query = ticket_query.filter(Ticket.created_at < end_dt)

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
        # priority tier's astrologers; this table is its own view. Date
        # range still applies (see _get_kam_performance's docstring).
        "kam_performance": _get_kam_performance(db, None, date_from=date_from, date_to=date_to),
        "weekly_ticket_trend": _ticket_period_trend(
            db, bucket="week", date_from=date_from, date_to=date_to
        ),
        "monthly_ticket_trend": _ticket_period_trend(
            db, bucket="month", date_from=date_from, date_to=date_to
        ),
    }
