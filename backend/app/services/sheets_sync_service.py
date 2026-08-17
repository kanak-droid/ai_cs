"""Pulls the ops team's external data (Google Sheets, plus one analytics
query) into Postgres.

Each tab/source has its own column layout (and the messier ones repeat a
header name or bury the key column somewhere in the middle — see
sheets_client.py), so columns are mapped by fixed position, checked against
the real data rather than assumed. Every sync is a full upsert-by-expert_id
overwrite — there's no history kept, since the chatbot only ever needs
"what's true right now."

Called from scripts/sync_sheets.py (the daily cron) and
POST /api/admin/sync-sheets (the ops "sync now" button) — both just call
sync_all(db).

2026-08-14: switched from Parth's test-copy sheets to the real KYC and
Payout sheets (settings.KYC_SPREADSHEET_ID / PAYOUT_SPREADSHEET_ID). The old
Supply Tracker sheet's queue-performance tab (priority/language) had no
replacement in either new sheet, so that sync step — and the old,
now-fully-redundant separate wallet-balance sync, since the payout sheet's
own cycle tab already has a wallet-balance column — was removed.
`_sync_expert_priority` (added same day) fills the priority half of that gap
from a saved analytics query instead of a sheet; language/talktime/queue
stats remain unsynced until ops shares a source for those specifically.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations import admin_mapping_client, analytics_client, sheets_client
from app.models.astrologer import Astrologer
from app.models.expert_priority import ExpertPriority
from app.models.sheet_sync import (
    SheetAstrologerRoster,
    SheetKycRecord,
    SheetPayoutStatus,
    SheetQueuePerformance,
)

logger = logging.getLogger(__name__)

_PRIORITY_TIER_TO_INT = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5}


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def _upsert(db: Session, model, expert_id: int, **fields) -> None:
    obj = db.get(model, expert_id)
    if obj is None:
        obj = model(expert_id=expert_id)
        db.add(obj)
    for key, value in fields.items():
        setattr(obj, key, value)
    # A newly-added object only enters the identity map on flush — without
    # this, a duplicate expert_id later in the same sheet (the KYC tab has a
    # few) wouldn't be found by db.get() above and would insert a second row
    # with the same primary key instead of overwriting this one.
    db.flush()


def _sync_roster(db: Session) -> int:
    header, rows = sheets_client.read_tab(settings.PAYOUT_SPREADSHEET_ID, "Expert ID", header_row=1)
    count = 0
    for row in rows:
        expert_id = _to_int(sheets_client.cell(row, 1))
        if expert_id is None:
            continue
        _upsert(
            db,
            SheetAstrologerRoster,
            expert_id,
            name=sheets_client.cell(row, 0),
            phone_number=sheets_client.cell(row, 2),
        )
        count += 1
    return count


def _sync_kyc(db: Session) -> int:
    header, rows = sheets_client.read_tab(settings.KYC_SPREADSHEET_ID, "KYC", header_row=1)
    count = 0
    for row in rows:
        expert_id = _to_int(sheets_client.cell(row, 22))
        if expert_id is None:
            continue
        _upsert(
            db,
            SheetKycRecord,
            expert_id,
            expert_name=sheets_client.cell(row, 23),
            kyc_status=sheets_client.cell(row, 1),
            verification_status=sheets_client.cell(row, 5),
            entry_status=sheets_client.cell(row, 20),
            message=sheets_client.cell(row, 21),
        )
        count += 1
    return count


def _sync_expert_priority(db: Session) -> int:
    rows = analytics_client.fetch_csv(settings.PRIORITY_QUERY_CSV_URL)
    count = 0
    for row in rows:
        expert_id = _to_int(row.get("expert_id"))
        if expert_id is None:
            continue
        tier = (row.get("current_priority") or "").strip() or None
        _upsert(
            db,
            ExpertPriority,
            expert_id,
            user_id=_to_int(row.get("user_id")),
            expert_name=row.get("expert_name"),
            current_priority_tier=tier,
            priority=_PRIORITY_TIER_TO_INT.get(tier) if tier else None,
        )
        count += 1
    return count


def _sync_payout_status(db: Session) -> int:
    header, rows = sheets_client.read_tab(
        settings.PAYOUT_SPREADSHEET_ID, settings.PAYOUT_CYCLE_TAB, header_row=1
    )
    count = 0
    for row in rows:
        expert_id = _to_int(sheets_client.cell(row, 1))
        if expert_id is None:
            continue
        _upsert(
            db,
            SheetPayoutStatus,
            expert_id,
            name=sheets_client.cell(row, 2),
            wallet_balance=_to_int(sheets_client.cell(row, 4)),
            payout=_to_int(sheets_client.cell(row, 5)),
            incentive=_to_int(sheets_client.cell(row, 6)),
            penalty_amount=_to_int(sheets_client.cell(row, 8)),
            kyc_status=sheets_client.cell(row, 12),
            tds_deducted_percent=sheets_client.cell(row, 13),
            tds_amount=_to_int(sheets_client.cell(row, 14)),
            total_after_tax=_to_int(sheets_client.cell(row, 15)),
            status=sheets_client.cell(row, 19),
            processed_at=sheets_client.cell(row, 20),
            cycle_tab=settings.PAYOUT_CYCLE_TAB,
        )
        count += 1
    return count


def _provision_new_astrologers(db: Session) -> int:
    """Creates a real Astrologer row for any expert who shows up in the
    priority-ranking query (i.e. has real call/booking activity) but has no
    Astrologer row linked to their expert_id yet.

    Without this, a brand-new database never has anyone a real astrologer's
    JWT (keyed by plain user_id — see auth_service.resolve_astrologer_by_user_id)
    can actually resolve to, even though the source data already has the
    link — confirmed live 2026-08-18: every real user_id got "session
    expired" against a fresh production database with zero linked rows,
    despite the priority query itself having real expert_id/user_id pairs.

    Deliberately scoped to the priority query, not the full roster sheet —
    an expert with no call/booking activity yet isn't a real user of this
    product regardless of whether ops has them in the roster.

    New astrologer's KAM is assigned through the same language-matched
    round-robin as everything else (admin_mapping_client), applied the
    first time they're seen here — not a separate/different assignment path.
    """
    already_linked = {
        expert_id
        for (expert_id,) in db.execute(
            select(Astrologer.expert_id).where(Astrologer.expert_id.is_not(None))
        )
    }
    candidates = [
        row for row in db.scalars(select(ExpertPriority)).all() if row.expert_id not in already_linked
    ]

    count = 0
    for priority_row in candidates:
        roster = db.get(SheetAstrologerRoster, priority_row.expert_id)
        queue_performance = db.get(SheetQueuePerformance, priority_row.expert_id)
        name = (roster.name if roster else None) or priority_row.expert_name or f"Expert {priority_row.expert_id}"
        astrologer = Astrologer(
            name=name,
            phone=(roster.phone_number if roster else None) or "",
            language=(
                queue_performance.languages
                if queue_performance and queue_performance.languages
                else "English"
            ),
            expert_id=priority_row.expert_id,
            user_id=priority_row.user_id,
        )
        db.add(astrologer)
        db.flush()  # assigns astrologer.id, needed for the KAM round-robin below

        assignment = admin_mapping_client.get_assigned_admin(db, astrologer.id)
        astrologer.assigned_admin_id = assignment.admin_id
        count += 1
    return count


def _sync_astrologer_profiles(db: Session) -> int:
    """Linking an Astrologer to a real expert_id (§8a) only wired up identity
    (name, id) — their phone/language kept whatever scripts/seed.py originally
    put there. This overwrites phone from the just-synced roster; language
    still comes from SheetQueuePerformance, which (2026-08-14) has no active
    sync step, so it only reflects whatever was synced before the old
    Supply Tracker sheet was retired — stale but real, not fabricated.

    Also backfills user_id from the priority sync (added to that query
    2026-08-14) — this is the real platform identity a real astrologer JWT
    is actually keyed by, distinct from expert_id.
    """
    linked = db.scalars(select(Astrologer).where(Astrologer.expert_id.is_not(None))).all()
    count = 0
    for astrologer in linked:
        roster = db.get(SheetAstrologerRoster, astrologer.expert_id)
        queue_performance = db.get(SheetQueuePerformance, astrologer.expert_id)
        priority_row = db.get(ExpertPriority, astrologer.expert_id)
        changed = False
        if roster and roster.phone_number and astrologer.phone != roster.phone_number:
            astrologer.phone = roster.phone_number
            changed = True
        if (
            queue_performance
            and queue_performance.languages
            and astrologer.language != queue_performance.languages
        ):
            astrologer.language = queue_performance.languages
            changed = True
        if (
            priority_row
            and priority_row.user_id is not None
            and astrologer.user_id != priority_row.user_id
        ):
            astrologer.user_id = priority_row.user_id
            changed = True
        if changed:
            count += 1
    return count


_SYNC_STEPS = [
    ("roster", _sync_roster),
    ("kyc", _sync_kyc),
    ("payout_status", _sync_payout_status),
    ("expert_priority", _sync_expert_priority),
    ("provisioned_astrologers", _provision_new_astrologers),
    ("astrologer_profiles", _sync_astrologer_profiles),
]


def sync_all(db: Session) -> dict[str, int | str]:
    """Runs every sync step; one step failing (e.g. a renamed tab) doesn't
    stop the others, since they're independent tables. Each step commits on
    its own — a later failure's rollback must only undo that step's own
    uncommitted work, never a prior step that already succeeded.
    """
    results: dict[str, int | str] = {}
    for name, step in _SYNC_STEPS:
        try:
            results[name] = step(db)
            db.commit()
        except Exception:
            logger.exception("Sheet sync step %r failed", name)
            db.rollback()
            results[name] = "error"
    return results
