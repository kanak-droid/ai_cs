from sqlalchemy.exc import IntegrityError

from app.models.astrologer import Astrologer
from app.models.expert_priority import ExpertPriority
from app.models.sheet_sync import SheetAstrologerRoster, SheetQueuePerformance
from app.services import sheets_sync_service


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
