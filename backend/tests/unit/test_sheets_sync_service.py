from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.integrations import sheets_client
from app.models.astrologer import Astrologer
from app.models.expert_priority import ExpertPriority
from app.models.payout_cycle_info import PayoutCycleInfo
from app.models.sheet_sync import SheetAstrologerRoster, SheetPayoutStatus, SheetQueuePerformance
from app.services import sheets_sync_service


def test_upsert_many_updates_an_existing_row_in_place(db_session):
    db_session.add(SheetAstrologerRoster(expert_id=601, name="Old Name", phone_number="+91-1"))
    db_session.commit()

    count = sheets_sync_service._upsert_many(
        db_session, SheetAstrologerRoster, [(601, {"name": "New Name", "phone_number": "+91-2"})]
    )

    assert count == 1
    row = db_session.query(SheetAstrologerRoster).filter_by(expert_id=601).one()
    assert row.name == "New Name"
    assert row.phone_number == "+91-2"


def test_upsert_many_collapses_a_duplicate_expert_id_within_the_same_batch(db_session):
    # The KYC tab has a few repeated expert_ids — the later row in the same
    # batch must win, not create a second row with the same primary key.
    count = sheets_sync_service._upsert_many(
        db_session,
        SheetAstrologerRoster,
        [
            (602, {"name": "First Pass", "phone_number": "+91-1"}),
            (602, {"name": "Second Pass", "phone_number": "+91-2"}),
        ],
    )

    assert count == 2
    rows = db_session.scalars(select(SheetAstrologerRoster).where(SheetAstrologerRoster.expert_id == 602)).all()
    assert len(rows) == 1
    assert rows[0].name == "Second Pass"
    assert rows[0].phone_number == "+91-2"


def test_provisions_a_new_astrologer_for_an_unlinked_priority_row(db_session, seeded_admin):
    db_session.add(ExpertPriority(expert_id=501, user_id=90501, expert_name="Astro Test", priority=2))
    db_session.add(SheetAstrologerRoster(expert_id=501, name="Astro Test", phone_number="+91-90000-00501"))
    db_session.add(SheetQueuePerformance(expert_id=501, languages="Hindi,Telugu"))
    db_session.commit()

    count = sheets_sync_service._provision_new_astrologers(db_session)

    assert count == 1
    astrologer = db_session.query(Astrologer).filter_by(expert_id=501).one()
    assert astrologer.user_id == 90501
    assert astrologer.name == "Astro Test"
    assert astrologer.phone == "+91-90000-00501"
    assert astrologer.language == "Hindi,Telugu"
    assert astrologer.assigned_admin_id == seeded_admin.id


def test_does_not_duplicate_an_already_linked_expert(db_session, seeded_admin):
    db_session.add(
        Astrologer(name="Existing", phone="+91-1", language="English", expert_id=502, user_id=90502)
    )
    db_session.add(ExpertPriority(expert_id=502, user_id=90502, expert_name="Existing", priority=3))
    db_session.commit()

    count = sheets_sync_service._provision_new_astrologers(db_session)

    assert count == 0
    assert db_session.query(Astrologer).filter_by(expert_id=502).count() == 1


def test_falls_back_to_expert_name_and_english_when_roster_data_is_missing(db_session, seeded_admin):
    # No SheetAstrologerRoster / SheetQueuePerformance row for this expert —
    # a real gap that shouldn't crash provisioning, just fall back safely.
    db_session.add(ExpertPriority(expert_id=503, user_id=90503, expert_name="Only In Priority Query"))
    db_session.commit()

    count = sheets_sync_service._provision_new_astrologers(db_session)

    assert count == 1
    astrologer = db_session.query(Astrologer).filter_by(expert_id=503).one()
    assert astrologer.name == "Only In Priority Query"
    assert astrologer.phone == ""
    assert astrologer.language == "English"


def test_falls_back_to_a_generic_name_when_even_expert_name_is_missing(db_session, seeded_admin):
    db_session.add(ExpertPriority(expert_id=504, user_id=90504, expert_name=None))
    db_session.commit()

    sheets_sync_service._provision_new_astrologers(db_session)

    astrologer = db_session.query(Astrologer).filter_by(expert_id=504).one()
    assert astrologer.name == "Expert 504"


def test_skips_a_row_that_collides_with_a_concurrent_sync_call_instead_of_aborting(
    db_session, seeded_admin, monkeypatch
):
    # Simulates two overlapping "Sync now" calls both deciding expert_id=505
    # is still unlinked before either commits — a real production crash
    # (2026-08-18, UniqueViolation on expert_id=4) that took down the whole
    # provisioning step, silently skipping every candidate queued after the
    # collision. The per-row SAVEPOINT should isolate just the losing row.
    db_session.add(ExpertPriority(expert_id=505, user_id=90505, expert_name="Race Loser"))
    db_session.add(ExpertPriority(expert_id=506, user_id=90506, expert_name="Race Winner"))
    db_session.commit()

    real_flush = db_session.flush

    def flaky_flush(*args, **kwargs):
        # Only the loop's own explicit flush (with the losing row still
        # pending) should fail — autoflushes triggered by the earlier
        # lookup queries must go through untouched.
        pending_loser = any(
            isinstance(obj, Astrologer) and obj.expert_id == 505 for obj in db_session.new
        )
        if pending_loser:
            raise IntegrityError("INSERT", {}, Exception("duplicate key value violates unique constraint"))
        return real_flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", flaky_flush)

    count = sheets_sync_service._provision_new_astrologers(db_session)

    assert count == 1
    assert db_session.query(Astrologer).filter_by(expert_id=505).count() == 0
    winner = db_session.query(Astrologer).filter_by(expert_id=506).one()
    assert winner.user_id == 90506
    assert winner.assigned_admin_id == seeded_admin.id


def test_parses_a_plain_month_day_cycle_tab_title():
    parsed = sheets_sync_service._parse_cycle_tab_date("August 14", today=date(2026, 8, 18))
    assert parsed == date(2026, 8, 14)


def test_parses_a_cycle_tab_title_with_a_trailing_cycle_number_suffix():
    # "July 31 - 1" — the " - 1" is a cycle-number suffix, not part of the date.
    parsed = sheets_sync_service._parse_cycle_tab_date("July 31 - 1", today=date(2026, 8, 18))
    assert parsed == date(2026, 7, 31)


def test_resolves_the_year_across_a_new_year_boundary():
    # Today is early January; a "December 31" tab is last year's, not this year's.
    parsed = sheets_sync_service._parse_cycle_tab_date("December 31", today=date(2026, 1, 3))
    assert parsed == date(2025, 12, 31)


def test_parses_a_three_letter_month_abbreviation():
    # Confirmed live 2026-08-18 against the real payout sheet: most tabs use
    # 3-letter abbreviations ("Aug 14"), not full names ("August 14") — a
    # month-name-only lookup silently failed on every single one of these,
    # including the actual latest tabs at the time, quietly falling back to
    # the newest FULL-name tab instead ("July 31"), which was weeks stale.
    parsed = sheets_sync_service._parse_cycle_tab_date("Aug 14 - 1", today=date(2026, 8, 18))
    assert parsed == date(2026, 8, 14)


def test_never_resolves_a_cycle_tab_to_a_date_far_in_the_future():
    # Confirmed live 2026-08-18: picking whichever year is numerically
    # closest to today resolved a "Jan 30" tab seen in August to *next*
    # January (~165 days away) instead of the one that already happened
    # (~200 days ago) — 165 < 200, even though these tabs are never really
    # months in the future. Must prefer the past/current candidate instead.
    parsed = sheets_sync_service._parse_cycle_tab_date("Jan 30 - 2", today=date(2026, 8, 18))
    assert parsed == date(2026, 1, 30)


def test_returns_none_for_a_title_with_no_recognizable_date():
    assert sheets_sync_service._parse_cycle_tab_date("Summary", today=date(2026, 8, 18)) is None


def test_next_payout_date_is_fourteen_days_after_the_latest_cycle():
    next_date = sheets_sync_service._next_payout_date(date(2026, 8, 14), today=date(2026, 8, 18))
    assert next_date == date(2026, 8, 28)


def test_next_payout_date_advances_past_today_when_sync_is_behind():
    # The latest known cycle is more than one 14-day step in the past —
    # e.g. ops hasn't added this fortnight's tab yet — so the next payout
    # date must still land in the future, not repeat a date already passed.
    next_date = sheets_sync_service._next_payout_date(date(2026, 7, 1), today=date(2026, 8, 18))
    assert next_date > date(2026, 8, 18)


def test_latest_payout_cycle_picks_the_most_recent_tab(monkeypatch):
    monkeypatch.setattr(
        sheets_client,
        "list_tab_titles",
        lambda spreadsheet_id: ["Summary", "July 31 - 1", "August 14", "June 17"],
    )

    result = sheets_sync_service._latest_payout_cycle(today=date(2026, 8, 18))

    assert result == ("August 14", date(2026, 8, 14))


def test_latest_payout_cycle_breaks_a_date_tie_toward_the_higher_cycle_number(monkeypatch):
    # The real sheet has multiple tabs per date ("Aug 14 - 1", "Aug 14 - 2",
    # sometimes "- 3") — the highest-numbered one is assumed to be the most
    # complete/final version of that date's data.
    monkeypatch.setattr(
        sheets_client,
        "list_tab_titles",
        lambda spreadsheet_id: ["Aug 14 - 1", "Aug 14 - 3", "Aug 14 - 2"],
    )

    result = sheets_sync_service._latest_payout_cycle(today=date(2026, 8, 18))

    assert result == ("Aug 14 - 3", date(2026, 8, 14))


def test_latest_payout_cycle_returns_none_when_listing_tabs_fails(monkeypatch):
    def _raise(spreadsheet_id):
        raise RuntimeError("Sheets API unavailable")

    monkeypatch.setattr(sheets_client, "list_tab_titles", _raise)

    assert sheets_sync_service._latest_payout_cycle(today=date(2026, 8, 18)) is None


def test_sync_payout_status_auto_detects_the_latest_cycle_tab_and_records_it(db_session, monkeypatch):
    monkeypatch.setattr(
        sheets_client, "list_tab_titles", lambda spreadsheet_id: ["July 31 - 1", "August 14"]
    )

    def fake_read_tab(spreadsheet_id, tab_title, header_row):
        assert tab_title == "August 14"  # the auto-detected latest, not settings.PAYOUT_CYCLE_TAB
        header = [""] * 20
        row = [""] * 20
        row[1] = "601"
        return header, [row]

    monkeypatch.setattr(sheets_client, "read_tab", fake_read_tab)

    count = sheets_sync_service._sync_payout_status(db_session, today=date(2026, 8, 18))

    assert count == 1
    row = db_session.query(SheetPayoutStatus).filter_by(expert_id=601).one()
    assert row.cycle_tab == "August 14"

    info = db_session.get(PayoutCycleInfo, 1)
    assert info is not None
    assert info.latest_cycle_tab == "August 14"
    assert info.latest_cycle_date == date(2026, 8, 14)
    assert info.next_payout_date == date(2026, 8, 28)
