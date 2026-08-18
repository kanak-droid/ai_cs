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

import calendar
import logging
import re
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utcnow
from app.integrations import admin_mapping_client, analytics_client, sheets_client
from app.models.astrologer import Astrologer
from app.models.expert_priority import ExpertPriority
from app.models.payout_cycle_info import PayoutCycleInfo
from app.models.sheet_sync import (
    SheetAstrologerRoster,
    SheetKycRecord,
    SheetPayoutStatus,
    SheetQueuePerformance,
)

logger = logging.getLogger(__name__)

_PRIORITY_TIER_TO_INT = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5}

_PAYOUT_CYCLE_DAYS = 14  # payouts run every alternate Friday

_MONTH_NAME_TO_NUMBER = {
    # Real tab titles mix full names ("July 31") and 3-letter abbreviations
    # ("Aug 14") inconsistently — confirmed live 2026-08-18: every single
    # abbreviated tab (which included the actual latest ones at the time)
    # silently failed to parse with only calendar.month_name, so this
    # quietly fell back to the newest FULL-name tab instead ("July 31"),
    # weeks stale. Both forms are indexed so neither can silently vanish
    # like that again.
    **{name.lower(): i for i, name in enumerate(calendar.month_name) if name},
    **{abbr.lower(): i for i, abbr in enumerate(calendar.month_abbr) if abbr},
}
# Cycle tabs are named like "July 31" or "Aug 14 - 1" — a month name, a day
# number, and sometimes a " - <n>" cycle-number suffix that isn't part of
# the date at all, so only the leading "Month Day" is matched.
_CYCLE_TAB_DATE_RE = re.compile(r"^([A-Za-z]+)\s+(\d{1,2})")
# The real sheet has multiple tabs per date ("Aug 14 - 1", "Aug 14 - 2",
# occasionally a stray "- 3") — these are NOT sequential revisions of the
# same data. Per ops (2026-08-18): "-1" is AstroLokal's own sheet, "-2" is
# a Razorpay-formatted copy for payment processing, and we always want "-1"
# specifically — "pick the highest number" (an earlier, wrong assumption)
# can silently pick Razorpay's copy, or some other stray tab, instead.
# Matched separately from the date itself since the spacing around the
# dash is inconsistent ("Jun 19 -1", "Sep 26-3").
_CYCLE_NUMBER_RE = re.compile(r"-\s*(\d+)")
_CANONICAL_CYCLE_NUMBER = 1


def _parse_cycle_tab_date(title: str, today: date) -> date | None:
    """Resolves a cycle tab's title to a real date. Tab titles carry no
    year, so it's inferred against `today`: these tabs are always for an
    already-elapsed or just-elapsing cycle, never far in the future.

    Picking whichever candidate year is numerically closest to today (by
    absolute distance) gets this backwards for tabs from earlier in the
    calendar year: confirmed live 2026-08-18, a "Jan 30" tab seen when today
    was in August resolved to the *next* January (~165 days away) instead
    of the one that already happened (~200 days ago), since 165 < 200 —
    despite next January being a future date these tabs never actually are.
    A small forward buffer still tolerates a tab added a day or two ahead
    of its nominal date.
    """
    match = _CYCLE_TAB_DATE_RE.match(title.strip())
    if not match:
        return None
    month = _MONTH_NAME_TO_NUMBER.get(match.group(1).lower())
    if month is None:
        return None
    day = int(match.group(2))
    candidates = []
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            continue
    if not candidates:
        return None
    not_future = [d for d in candidates if d <= today + timedelta(days=3)]
    pool = not_future or candidates
    return min(pool, key=lambda d: abs((d - today).days))


def _cycle_number(title: str) -> int:
    match = _CYCLE_NUMBER_RE.search(title)
    return int(match.group(1)) if match else 0


def _latest_payout_cycle(today: date) -> tuple[str, date] | None:
    """Finds whichever tab in the payout spreadsheet represents the most
    recent cycle, so ops never has to hand-update settings.PAYOUT_CYCLE_TAB
    every time a new one is added (every other Friday). Falls back to that
    setting (returns None here) if listing/parsing tabs doesn't turn up
    anything usable — e.g. the sheet's naming convention changes.
    """
    try:
        titles = sheets_client.list_tab_titles(settings.PAYOUT_SPREADSHEET_ID)
    except Exception:
        logger.exception("Could not list payout spreadsheet tabs")
        return None
    dated = [
        (title, parsed)
        for title in titles
        if (parsed := _parse_cycle_tab_date(title, today)) is not None
    ]
    if not dated:
        return None
    max_date = max(cycle_date for _, cycle_date in dated)
    same_date = [(title, cycle_date) for title, cycle_date in dated if cycle_date == max_date]
    # Always "-1" specifically — see _CYCLE_NUMBER_RE's comment. Falls back
    # to whichever cycle number is lowest if "-1" isn't there for some
    # reason (shouldn't happen per ops, but better than returning nothing).
    for title, cycle_date in same_date:
        if _cycle_number(title) == _CANONICAL_CYCLE_NUMBER:
            return title, cycle_date
    logger.warning(
        "No cycle-1 tab found for the latest payout date %s among %s — falling back to the "
        "lowest cycle number available",
        max_date,
        [title for title, _ in same_date],
    )
    return min(same_date, key=lambda pair: _cycle_number(pair[0]))


def _next_payout_date(latest_cycle_date: date, today: date) -> date:
    """Payouts run every alternate Friday — the next one is 14 days after
    the latest processed cycle, advanced by further 14-day steps if that
    sync lags behind (e.g. a new cycle tab hasn't been added yet even
    though one is due), so this is always a genuinely upcoming date.
    """
    next_date = latest_cycle_date + timedelta(days=_PAYOUT_CYCLE_DAYS)
    while next_date <= today:
        next_date += timedelta(days=_PAYOUT_CYCLE_DAYS)
    return next_date


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


def _upsert_many(db: Session, model, entries: list[tuple[int, dict]]) -> int:
    """Upserts every (expert_id, fields) entry against one preloaded snapshot
    of the table instead of one db.get() + db.flush() round trip per row —
    with a few thousand rows per sheet, that per-row pattern alone added up
    to tens of thousands of sequential round trips across a single sync,
    slow enough to blow past the ingress timeout (observed live 2026-08-18).

    The local `existing` dict is kept up to date as rows are added, so a
    duplicate expert_id later in the same sheet (the KYC tab has a few)
    still overwrites the earlier one instead of inserting a second row with
    the same primary key — the same guarantee the old per-row flush gave,
    without needing a flush to get it.
    """
    existing = {obj.expert_id: obj for obj in db.scalars(select(model)).all()}
    for expert_id, fields in entries:
        obj = existing.get(expert_id)
        if obj is None:
            obj = model(expert_id=expert_id)
            db.add(obj)
            existing[expert_id] = obj
        for key, value in fields.items():
            setattr(obj, key, value)
    db.flush()
    return len(entries)


def _sync_roster(db: Session) -> int:
    header, rows = sheets_client.read_tab(settings.PAYOUT_SPREADSHEET_ID, "Expert ID", header_row=1)
    entries = []
    for row in rows:
        expert_id = _to_int(sheets_client.cell(row, 1))
        if expert_id is None:
            continue
        entries.append((
            expert_id,
            {"name": sheets_client.cell(row, 0), "phone_number": sheets_client.cell(row, 2)},
        ))
    return _upsert_many(db, SheetAstrologerRoster, entries)


def _sync_kyc(db: Session) -> int:
    header, rows = sheets_client.read_tab(settings.KYC_SPREADSHEET_ID, "KYC", header_row=1)
    entries = []
    for row in rows:
        expert_id = _to_int(sheets_client.cell(row, 22))
        if expert_id is None:
            continue
        entries.append((
            expert_id,
            {
                "expert_name": sheets_client.cell(row, 23),
                "kyc_status": sheets_client.cell(row, 1),
                "verification_status": sheets_client.cell(row, 5),
                "entry_status": sheets_client.cell(row, 20),
                "message": sheets_client.cell(row, 21),
            },
        ))
    return _upsert_many(db, SheetKycRecord, entries)


def _sync_expert_priority(db: Session) -> int:
    rows = analytics_client.fetch_csv(settings.PRIORITY_QUERY_CSV_URL)
    entries = []
    for row in rows:
        expert_id = _to_int(row.get("expert_id"))
        if expert_id is None:
            continue
        tier = (row.get("current_priority") or "").strip() or None
        entries.append((
            expert_id,
            {
                "user_id": _to_int(row.get("user_id")),
                "expert_name": row.get("expert_name"),
                "current_priority_tier": tier,
                "priority": _PRIORITY_TIER_TO_INT.get(tier) if tier else None,
            },
        ))
    return _upsert_many(db, ExpertPriority, entries)


def _sync_payout_status(db: Session, *, today: date | None = None) -> int:
    today = today or utcnow().date()
    latest = _latest_payout_cycle(today)
    cycle_tab = latest[0] if latest else settings.PAYOUT_CYCLE_TAB

    header, rows = sheets_client.read_tab(settings.PAYOUT_SPREADSHEET_ID, cycle_tab, header_row=1)
    entries = []
    for row in rows:
        expert_id = _to_int(sheets_client.cell(row, 1))
        if expert_id is None:
            continue
        entries.append((
            expert_id,
            {
                "name": sheets_client.cell(row, 2),
                "wallet_balance": _to_int(sheets_client.cell(row, 4)),
                "payout": _to_int(sheets_client.cell(row, 5)),
                "incentive": _to_int(sheets_client.cell(row, 6)),
                "penalty_amount": _to_int(sheets_client.cell(row, 8)),
                "kyc_status": sheets_client.cell(row, 12),
                "tds_deducted_percent": sheets_client.cell(row, 13),
                "tds_amount": _to_int(sheets_client.cell(row, 14)),
                "total_after_tax": _to_int(sheets_client.cell(row, 15)),
                "status": sheets_client.cell(row, 19),
                "processed_at": sheets_client.cell(row, 20),
                "cycle_tab": cycle_tab,
            },
        ))
    count = _upsert_many(db, SheetPayoutStatus, entries)

    if latest is not None:
        _, latest_cycle_date = latest
        info = db.get(PayoutCycleInfo, 1) or PayoutCycleInfo(id=1)
        info.latest_cycle_tab = cycle_tab
        info.latest_cycle_date = latest_cycle_date
        info.next_payout_date = _next_payout_date(latest_cycle_date, today)
        db.add(info)

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

    Each row's insert is wrapped in its own SAVEPOINT: with up to a few
    thousand candidates on the very first run, two overlapping sync calls
    (a double-click of "Sync now", or a retry landing while an earlier one
    was still mid-flight) can both decide the same expert_id is still
    unlinked before either commits — the second one's insert then hits
    ix_astrologers_expert_id's unique constraint. Observed live 2026-08-18:
    that crashed this entire step, and every candidate after the collision
    in the batch silently never got provisioned. A per-row savepoint means
    one collision just skips that one expert (it's already provisioned by
    the other call) instead of aborting the whole batch.

    KAMs, the roster, and queue-performance data are all preloaded once up
    front rather than re-queried per candidate (via db.get() and the usual
    admin_mapping_client.get_assigned_admin(), which does its own KAM table
    scan plus an astrologer re-fetch). With a few thousand candidates on the
    first real run, those per-row round trips made this step slow enough to
    blow past the ingress timeout (observed live 2026-08-18: the request
    never came back, though the sync kept running server-side). Only the
    insert itself still needs its own round trip per row — Postgres doesn't
    hand out the new Astrologer.id needed for the KAM round-robin below
    until the row is actually flushed.
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
    if not candidates:
        return 0
    kams = admin_mapping_client.fetch_active_kams(db)
    rosters = {obj.expert_id: obj for obj in db.scalars(select(SheetAstrologerRoster)).all()}
    queue_performances = {obj.expert_id: obj for obj in db.scalars(select(SheetQueuePerformance)).all()}

    count = 0
    for priority_row in candidates:
        roster = rosters.get(priority_row.expert_id)
        queue_performance = queue_performances.get(priority_row.expert_id)
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
        try:
            with db.begin_nested():
                db.flush()  # assigns astrologer.id, needed for the KAM round-robin below
        except IntegrityError:
            # The SAVEPOINT rollback undoes the failed INSERT but does not
            # remove the object from the session's pending set — left alone,
            # the very next autoflush (e.g. the db.get() calls below, for the
            # *next* candidate) retries this same doomed insert and raises
            # again, uncaught, outside this except. Must expunge explicitly.
            db.expunge(astrologer)
            logger.warning(
                "Skipping expert_id=%s — provisioned concurrently by another sync call",
                priority_row.expert_id,
            )
            continue

        kam = admin_mapping_client.pick_kam(kams, language=astrologer.language, index_id=astrologer.id)
        astrologer.assigned_admin_id = kam.id
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

    Roster/queue-performance/priority are preloaded once rather than via
    db.get() per linked astrologer — see _upsert_many's docstring for why
    that per-row pattern doesn't scale past a few hundred rows.
    """
    linked = db.scalars(select(Astrologer).where(Astrologer.expert_id.is_not(None))).all()
    rosters = {obj.expert_id: obj for obj in db.scalars(select(SheetAstrologerRoster)).all()}
    queue_performances = {obj.expert_id: obj for obj in db.scalars(select(SheetQueuePerformance)).all()}
    priority_rows = {obj.expert_id: obj for obj in db.scalars(select(ExpertPriority)).all()}
    count = 0
    for astrologer in linked:
        roster = rosters.get(astrologer.expert_id)
        queue_performance = queue_performances.get(astrologer.expert_id)
        priority_row = priority_rows.get(astrologer.expert_id)
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
