from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import NotFoundError
from app.integrations import queue_performance_client
from app.models.call import Call


def _attach_display_fields(db: Session, calls: list[Call]) -> None:
    cache: dict[int, int | None] = {}
    for call in calls:
        aid = call.astrologer_id
        if aid not in cache:
            cache[aid] = queue_performance_client.get_queue_performance(db, aid).priority
        call.priority = cache[aid]  # type: ignore[attr-defined]
        call.astrologer_name = call.astrologer.name  # type: ignore[attr-defined]


def list_call_logs(
    db: Session,
    *,
    resolution_status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[Call]:
    stmt = select(Call).options(joinedload(Call.astrologer))
    if resolution_status is not None:
        stmt = stmt.where(Call.resolution_status == resolution_status)
    if date_from is not None:
        stmt = stmt.where(Call.created_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        stmt = stmt.where(Call.created_at < datetime.combine(date_to + timedelta(days=1), time.min))
    stmt = stmt.order_by(Call.created_at.asc())
    calls = list(db.scalars(stmt).unique())
    calls.sort(key=lambda c: queue_performance_client.priority_sort_key(db, c.astrologer_id))
    _attach_display_fields(db, calls)
    return calls


def get_call_log(db: Session, call_id: int) -> Call:
    call = db.scalars(
        select(Call).where(Call.id == call_id).options(joinedload(Call.astrologer))
    ).one_or_none()
    if call is None:
        raise NotFoundError(f"Call {call_id} not found")
    _attach_display_fields(db, [call])
    return call
