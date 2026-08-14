# MOCKED — but only for astrologers with no linked expert_id.
#
# Astrologers whose `expert_id` has a synced row in expert_priority and/or
# sheet_queue_performance (see app/services/sheets_sync_service.py) get
# their REAL current priority ranking and queue stats instead of a
# fabricated one.
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.integrations.config import MOCK_MODE
from app.models.astrologer import Astrologer
from app.models.expert_priority import ExpertPriority
from app.models.sheet_sync import SheetQueuePerformance


@dataclass(frozen=True)
class QueuePerformance:
    astrologer_id: int
    # None means genuinely unranked (not enough matured users yet, or no
    # priority tier defined for this astrologer's language) — never
    # fabricated into a fake number. See ExpertPriority.priority.
    priority: int | None
    users_connected: int
    queues_connected: int
    total_talktime_min: int


def _real_queue_performance(
    db: Session, astrologer_id: int, expert_id: int
) -> QueuePerformance | None:
    synced = db.get(SheetQueuePerformance, expert_id)
    priority_row = db.get(ExpertPriority, expert_id)
    if synced is None and priority_row is None:
        return None

    # Prefer the live priority-query source; fall back to the old (frozen
    # since 2026-08-14) sheet-synced value only if this expert has NO row
    # in the new source at all — a row that exists but is None (PRE_MATURE/
    # blank) is a confirmed "unranked," not missing data, so it must NOT
    # fall back to a stale number.
    if priority_row is not None:
        priority = priority_row.priority
    else:
        priority = synced.priority if synced else None

    return QueuePerformance(
        astrologer_id=astrologer_id,
        priority=priority,
        users_connected=(synced.users_connected or 0) if synced else 0,
        queues_connected=(synced.queues_connected or 0) if synced else 0,
        total_talktime_min=(synced.total_talktime_min or 0) if synced else 0,
    )


def get_queue_performance(db: Session, astrologer_id: int) -> QueuePerformance:
    astrologer = db.get(Astrologer, astrologer_id)
    if astrologer and astrologer.expert_id:
        real = _real_queue_performance(db, astrologer_id, astrologer.expert_id)
        if real is not None:
            return real

    if not MOCK_MODE:
        raise NotImplementedError("Real queue-performance integration is not wired up yet.")

    # Deterministic per astrologer_id, same convention as payout_client/kyc_client.
    seed = astrologer_id % 5
    return QueuePerformance(
        astrologer_id=astrologer_id,
        priority=seed + 1,
        users_connected=50 + (astrologer_id * 13) % 200,
        queues_connected=60 + (astrologer_id * 17) % 250,
        total_talktime_min=300 + (astrologer_id * 23) % 1000,
    )
