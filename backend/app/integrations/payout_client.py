# MOCKED — replace with real API call.
#
# Real integration: this would call AstroLokal's payments service, e.g.
#   GET {PAYOUTS_API_URL}/astrologers/{astrologer_id}/payout-status
# and return its response shape instead of the fabricated PayoutStatus below.
# Nothing outside this file needs to change to make that swap.
from dataclasses import dataclass
from datetime import date, timedelta

from app.integrations.config import MOCK_MODE


@dataclass(frozen=True)
class PayoutStatus:
    astrologer_id: int
    status: str  # "scheduled" | "processing" | "paid" | "on_hold"
    amount_inr: int
    scheduled_date: str
    last_paid_date: str


def get_payout_status(astrologer_id: int) -> PayoutStatus:
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
