# MOCKED — replace with real API call.
#
# Real integration: this would call AstroLokal's KYC/compliance service, e.g.
#   GET {KYC_API_URL}/astrologers/{astrologer_id}/kyc-status
# Nothing outside this file needs to change to make that swap.
from dataclasses import dataclass

from app.integrations.config import MOCK_MODE


@dataclass(frozen=True)
class KycStatus:
    astrologer_id: int
    status: str  # "verified" | "pending" | "rejected" | "not_submitted"
    reason: str | None


def get_kyc_status(astrologer_id: int) -> KycStatus:
    if not MOCK_MODE:
        raise NotImplementedError("Real KYC integration is not wired up yet.")

    seed = astrologer_id % 4
    statuses = ["verified", "pending", "rejected", "not_submitted"]
    reasons = {
        "rejected": "PAN card image was blurry — please re-upload.",
        "pending": "Documents received, under manual review.",
    }
    status = statuses[seed]
    return KycStatus(astrologer_id=astrologer_id, status=status, reason=reasons.get(status))
