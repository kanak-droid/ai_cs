from datetime import date

from app.integrations import payout_client
from app.models.astrologer import Astrologer
from app.models.payout_cycle_info import PayoutCycleInfo
from app.models.sheet_sync import SheetPayoutStatus


def test_real_payout_status_reports_the_actual_next_payout_date(db_session, seeded_admin):
    astrologer = Astrologer(
        name="Linked Astrologer",
        phone="+91-1",
        language="English",
        expert_id=701,
        user_id=90701,
        assigned_admin_id=seeded_admin.id,
    )
    db_session.add(astrologer)
    db_session.add(SheetPayoutStatus(expert_id=701, status="processed", total_after_tax=9000))
    db_session.add(
        PayoutCycleInfo(
            id=1,
            latest_cycle_tab="August 14",
            latest_cycle_date=date(2026, 8, 14),
            next_payout_date=date(2026, 8, 28),
        )
    )
    db_session.commit()

    result = payout_client.get_payout_status(db_session, astrologer.id)

    assert result.scheduled_date == "2026-08-28"


def test_real_payout_status_falls_back_when_cycle_info_is_missing(db_session, seeded_admin):
    # Only possible if the auto-detection in sheets_sync_service never
    # successfully parsed a cycle tab yet — say so plainly rather than let
    # the model guess a date.
    astrologer = Astrologer(
        name="Linked Astrologer",
        phone="+91-1",
        language="English",
        expert_id=702,
        user_id=90702,
        assigned_admin_id=seeded_admin.id,
    )
    db_session.add(astrologer)
    db_session.add(SheetPayoutStatus(expert_id=702, status="processed", total_after_tax=9000))
    db_session.commit()

    result = payout_client.get_payout_status(db_session, astrologer.id)

    assert result.scheduled_date == "not tracked — could not determine the next cycle"
