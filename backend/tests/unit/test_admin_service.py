from datetime import timedelta

from app.core.time import utcnow
from app.models.admin import Admin
from app.models.enums import AdminRole
from app.services import admin_service


def _make_admin(db_session, **overrides) -> Admin:
    admin = Admin(name="Some Admin", email="some.admin@test.example", role=AdminRole.KAM, **overrides)
    db_session.add(admin)
    db_session.commit()
    return admin


def test_reverts_when_the_leave_until_date_has_passed(db_session):
    admin = _make_admin(
        db_session,
        is_temporarily_inactive=True,
        leave_until=(utcnow() - timedelta(days=1)).date(),
    )

    admin_service.maybe_end_scheduled_leave(db_session, admin)

    assert admin.is_temporarily_inactive is False
    assert admin.leave_until is None


def test_does_not_revert_when_the_leave_until_date_is_still_in_the_future(db_session):
    future = (utcnow() + timedelta(days=1)).date()
    admin = _make_admin(db_session, is_temporarily_inactive=True, leave_until=future)

    admin_service.maybe_end_scheduled_leave(db_session, admin)

    assert admin.is_temporarily_inactive is True
    assert admin.leave_until == future


def test_does_not_revert_an_indefinite_leave_with_no_end_date(db_session):
    admin = _make_admin(db_session, is_temporarily_inactive=True, leave_until=None)

    admin_service.maybe_end_scheduled_leave(db_session, admin)

    assert admin.is_temporarily_inactive is True


def test_is_a_no_op_when_not_on_leave(db_session):
    admin = _make_admin(
        db_session,
        is_temporarily_inactive=False,
        leave_until=(utcnow() - timedelta(days=1)).date(),
    )

    admin_service.maybe_end_scheduled_leave(db_session, admin)

    # Untouched — nothing to revert if the flag was already off.
    assert admin.leave_until is not None
