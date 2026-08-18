# MOCKED — but only for astrologers with no linked expert_id.
#
# Astrologers whose `expert_id` is set and has a synced row in
# sheet_payout_status (see app/services/sheets_sync_service.py) get their
# REAL current-cycle payout status instead of a fabricated one — this is the
# actual, no-longer-mocked path for anyone ops has linked.
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.integrations.config import MOCK_MODE
from app.models.astrologer import Astrologer
from app.models.payout_cycle_info import PayoutCycleInfo
from app.models.sheet_sync import SheetPayoutStatus


@dataclass(frozen=True)
class PayoutStatus:
    astrologer_id: int
    status: str  # "scheduled" | "processing" | "paid" | "on_hold" | (real) "processed" etc.
    amount_inr: int
    scheduled_date: str
    last_paid_date: str
    wallet_balance_inr: int | None = None
    # This cycle's KYC status ("YES"/"NO") and the TDS percent/amount
    # actually deducted — straight from the payout sheet, not guessed.
    # Incomplete KYC means a much higher TDS rate (~20% vs ~1%), the most
    # common reason a payout looks lower than expected — see prompt.py.
    kyc_status: str | None = None
    tds_deducted_percent: str | None = None
    tds_amount_inr: int | None = None
    # The sheet's own Incentive column — synced into SheetPayoutStatus all
    # along, but never actually surfaced here until now (confirmed live
    # 2026-08-18: an astrologer with a real nonzero incentive asked about it
    # and was told AstroLokal has no incentive scheme at all — the model
    # wasn't wrong to say payouts are the real earnings mechanism, but this
    # field being missing meant it couldn't also report the actual number).
    incentive_inr: int | None = None


def _real_payout_status(db: Session, astrologer_id: int, expert_id: int) -> PayoutStatus | None:
    synced = db.get(SheetPayoutStatus, expert_id)
    if synced is None:
        return None
    # Payouts run every alternate Friday; sheets_sync_service computes the
    # real next date from the payout spreadsheet's own tab names each sync
    # (see PayoutCycleInfo) — only missing if that auto-detection couldn't
    # parse any tab yet, in which case there's genuinely nothing real to
    # report, so say so explicitly rather than let the model guess one.
    cycle_info = db.get(PayoutCycleInfo, 1)
    scheduled_date = (
        cycle_info.next_payout_date.isoformat()
        if cycle_info
        else "not tracked — could not determine the next cycle"
    )
    return PayoutStatus(
        astrologer_id=astrologer_id,
        status=synced.status or "unknown",
        amount_inr=synced.total_after_tax or 0,
        scheduled_date=scheduled_date,
        last_paid_date=synced.processed_at or "unknown",
        wallet_balance_inr=synced.wallet_balance,
        kyc_status=synced.kyc_status,
        tds_deducted_percent=synced.tds_deducted_percent,
        tds_amount_inr=synced.tds_amount,
        incentive_inr=synced.incentive,
    )


def get_payout_status(db: Session, astrologer_id: int) -> PayoutStatus:
    astrologer = db.get(Astrologer, astrologer_id)
    if astrologer and astrologer.expert_id:
        real = _real_payout_status(db, astrologer_id, astrologer.expert_id)
        if real is not None:
            return real

    if not MOCK_MODE:
        raise NotImplementedError("Real payout integration is not wired up yet.")

    # Deterministic per astrologer_id so repeated calls / demos / tests are stable.
    seed = astrologer_id % 4
    statuses = ["scheduled", "processing", "paid", "on_hold"]
    today = date.today()
    return PayoutStatus(
        astrologer_id=astrologer_id,
        status=statuses[seed],
        amount_inr=8000 + (astrologer_id * 137) % 12000,
        scheduled_date=(today + timedelta(days=(5 - today.day) % 30 + 1)).isoformat(),
        last_paid_date=(today - timedelta(days=30)).isoformat(),
    )
