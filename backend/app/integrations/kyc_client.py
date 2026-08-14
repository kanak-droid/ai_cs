# MOCKED — but only for astrologers with no linked expert_id.
#
# Astrologers whose `expert_id` has a synced row in sheet_kyc_records (see
# app/services/sheets_sync_service.py) get their REAL KYC status. A linked
# expert with NO row there at all (most of the roster right now — the KYC
# sheet has a lot of catching up to do, per ops, 2026-08-14) is treated as
# "not_submitted" explicitly — never falls back to fabricated mock data,
# since we do have a real identity for them, just not yet a KYC record.
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.integrations.config import MOCK_MODE
from app.models.astrologer import Astrologer
from app.models.sheet_sync import SheetKycRecord

_STATUS_MAP = {"YES": "verified", "NO": "rejected"}


@dataclass(frozen=True)
class KycStatus:
    astrologer_id: int
    status: str  # "verified" | "pending" | "rejected" | "not_submitted"
    reason: str | None


def _real_kyc_status(db: Session, astrologer_id: int, expert_id: int) -> KycStatus:
    synced = db.get(SheetKycRecord, expert_id)
    if synced is None:
        return KycStatus(
            astrologer_id=astrologer_id,
            status="not_submitted",
            reason="No KYC submission found yet.",
        )
    status = _STATUS_MAP.get((synced.kyc_status or "").strip().upper(), "pending")
    reason = None
    if status != "verified":
        reason = synced.message or (
            f"Verification status: {synced.verification_status or 'unknown'}"
        )
    return KycStatus(astrologer_id=astrologer_id, status=status, reason=reason)


def get_kyc_status(db: Session, astrologer_id: int) -> KycStatus:
    astrologer = db.get(Astrologer, astrologer_id)
    if astrologer and astrologer.expert_id:
        return _real_kyc_status(db, astrologer_id, astrologer.expert_id)

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
