import pytest

from app.integrations import admin_mapping_client
from app.models.admin import Admin
from app.models.enums import AdminRole


def _make_kam(db_session, name: str) -> Admin:
    admin = Admin(name=name, email=f"{name.lower()}@test.example", role=AdminRole.KAM)
    db_session.add(admin)
    db_session.commit()
    return admin


def test_fetch_active_kams_excludes_a_kam_on_leave(db_session):
    # is_temporarily_inactive must be excluded from NEW round-robin
    # assignment the same as permanent deactivation, even though the admin
    # otherwise stays is_active=True (see Admin model's docstring).
    available = _make_kam(db_session, "Available")
    on_leave = _make_kam(db_session, "OnLeave")
    on_leave.is_temporarily_inactive = True
    db_session.commit()

    kams = admin_mapping_client.fetch_active_kams(db_session)

    assert [k.id for k in kams] == [available.id]


def test_fetch_active_kams_raises_when_every_kam_is_on_leave(db_session):
    only_kam = _make_kam(db_session, "OnlyKam")
    only_kam.is_temporarily_inactive = True
    db_session.commit()

    with pytest.raises(RuntimeError):
        admin_mapping_client.fetch_active_kams(db_session)
