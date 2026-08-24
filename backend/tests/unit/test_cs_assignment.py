from datetime import timedelta

from app.core.time import utcnow
from app.integrations import cs_assignment_client
from app.models.admin import Admin
from app.models.enums import AdminRole


def _make_cs(db_session, name: str, languages: list[str]) -> Admin:
    admin = Admin(name=name, email=f"{name.lower()}@test.example", role=AdminRole.CS, languages=languages)
    db_session.add(admin)
    db_session.commit()
    return admin


def test_returns_none_when_no_cs_admins_exist(db_session):
    result = cs_assignment_client.get_assigned_cs(db_session, ticket_id=1, astrologer_language="Hindi")
    assert result is None


def test_round_robins_within_the_matching_language_group(db_session):
    hindi_1 = _make_cs(db_session, "Hindi1", ["Hindi"])
    hindi_2 = _make_cs(db_session, "Hindi2", ["Hindi"])
    _make_cs(db_session, "TamilOnly", ["Tamil"])

    seen_ids = {
        cs_assignment_client.get_assigned_cs(
            db_session, ticket_id=ticket_id, astrologer_language="Hindi"
        ).admin_id
        for ticket_id in range(10)
    }

    # Only the two Hindi-serving CS admins are ever picked, never the Tamil one.
    assert seen_ids == {hindi_1.id, hindi_2.id}


def test_matches_an_astrologer_who_speaks_multiple_languages(db_session):
    tamil_cs = _make_cs(db_session, "TamilCS", ["Tamil"])
    _make_cs(db_session, "MalayalamCS", ["Malayalam"])

    result = cs_assignment_client.get_assigned_cs(
        db_session, ticket_id=0, astrologer_language="Bengali, Tamil"
    )

    assert result is not None
    assert result.admin_id == tamil_cs.id


def test_falls_back_to_the_full_cs_pool_when_no_language_matches(db_session):
    only_cs = _make_cs(db_session, "OnlyCS", ["Hindi"])

    result = cs_assignment_client.get_assigned_cs(
        db_session, ticket_id=0, astrologer_language="Bengali"
    )

    assert result is not None
    assert result.admin_id == only_cs.id


def test_ignores_inactive_and_non_cs_admins(db_session):
    inactive = _make_cs(db_session, "InactiveCS", ["Hindi"])
    inactive.is_active = False
    kam = Admin(name="AKam", email="akam@test.example", role=AdminRole.KAM, languages=["Hindi"])
    db_session.add(kam)
    db_session.commit()

    result = cs_assignment_client.get_assigned_cs(db_session, ticket_id=0, astrologer_language="Hindi")

    assert result is None


def test_ignores_a_cs_admin_on_leave(db_session):
    # On leave (is_temporarily_inactive) must be excluded from NEW
    # assignment the same as permanent deactivation, even though the admin
    # otherwise stays is_active=True (see Admin model's docstring).
    on_leave = _make_cs(db_session, "OnLeaveCS", ["Hindi"])
    on_leave.is_temporarily_inactive = True
    db_session.commit()

    result = cs_assignment_client.get_assigned_cs(db_session, ticket_id=0, astrologer_language="Hindi")

    assert result is None


def test_auto_reverts_a_cs_admin_whose_scheduled_leave_has_ended(db_session):
    back_from_leave = _make_cs(db_session, "BackFromLeaveCS", ["Hindi"])
    back_from_leave.is_temporarily_inactive = True
    back_from_leave.leave_until = (utcnow() - timedelta(days=1)).date()
    db_session.commit()

    result = cs_assignment_client.get_assigned_cs(db_session, ticket_id=0, astrologer_language="Hindi")

    assert result is not None
    assert result.admin_id == back_from_leave.id
    assert back_from_leave.is_temporarily_inactive is False
    assert back_from_leave.leave_until is None
