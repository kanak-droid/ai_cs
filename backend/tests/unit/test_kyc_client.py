from app.integrations import kyc_client
from app.integrations.config import MOCK_MODE
from app.models.astrologer import Astrologer
from app.models.sheet_sync import SheetKycRecord


def _linked_astrologer(db_session, expert_id: int) -> Astrologer:
    astrologer = Astrologer(name="Linked", phone="+91-1", language="Hindi", expert_id=expert_id)
    db_session.add(astrologer)
    db_session.commit()
    return astrologer


def test_linked_expert_with_no_kyc_row_is_not_submitted_not_mocked(db_session):
    # No SheetKycRecord at all for this expert_id — must be an explicit,
    # honest "not_submitted", never a fabricated mock status, since we do
    # have a real identity for them.
    astrologer = _linked_astrologer(db_session, expert_id=701)

    result = kyc_client.get_kyc_status(db_session, astrologer.id)

    assert result.status == "not_submitted"
    assert result.reason == "No KYC submission found yet."


def test_linked_expert_with_a_real_kyc_row_uses_it(db_session):
    astrologer = _linked_astrologer(db_session, expert_id=702)
    db_session.add(
        SheetKycRecord(
            expert_id=702,
            expert_name="Real Person",
            kyc_status="YES",
            verification_status="VALID",
            entry_status="SUCCESS",
            message=None,
        )
    )
    db_session.commit()

    result = kyc_client.get_kyc_status(db_session, astrologer.id)

    assert result.status == "verified"
    assert result.reason is None


def test_linked_expert_with_a_rejected_kyc_row_surfaces_the_reason(db_session):
    astrologer = _linked_astrologer(db_session, expert_id=703)
    db_session.add(
        SheetKycRecord(
            expert_id=703,
            expert_name="Real Person",
            kyc_status="NO",
            verification_status="INVALID",
            entry_status="FAILED",
            message="PAN name mismatch",
        )
    )
    db_session.commit()

    result = kyc_client.get_kyc_status(db_session, astrologer.id)

    assert result.status == "rejected"
    assert result.reason == "PAN name mismatch"


def test_unlinked_astrologer_still_gets_the_mock(db_session, seeded_astrologer):
    # seeded_astrologer has no expert_id — this path is untouched by the fix.
    result = kyc_client.get_kyc_status(db_session, seeded_astrologer.id)

    assert MOCK_MODE is True  # sanity: confirms we're actually exercising the mock branch
    assert result.status in {"verified", "pending", "rejected", "not_submitted"}
