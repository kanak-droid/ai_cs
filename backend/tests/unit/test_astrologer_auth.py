import pytest

from app.core.security import InvalidTokenError
from app.models.astrologer import Astrologer
from app.services import auth_service


def test_resolve_astrologer_by_user_id_finds_the_linked_astrologer(db_session, seeded_admin):
    astrologer = Astrologer(
        name="Real Astrologer",
        phone="+91-90000-00099",
        language="Tamil",
        user_id=123456,
        assigned_admin_id=seeded_admin.id,
    )
    db_session.add(astrologer)
    db_session.commit()

    context = auth_service.resolve_astrologer_by_user_id(db_session, 123456)

    assert context.astrologer_id == astrologer.id
    assert context.name == "Real Astrologer"
    assert context.language == "Tamil"


def test_resolve_astrologer_by_user_id_rejects_an_unknown_user_id(db_session):
    with pytest.raises(InvalidTokenError):
        auth_service.resolve_astrologer_by_user_id(db_session, 999999999)


def test_verify_astrologer_session_rejects_a_non_integer_value(db_session):
    with pytest.raises(InvalidTokenError):
        auth_service.verify_astrologer_session(db_session, "not-a-number")


def test_verify_astrologer_session_rejects_an_unlinked_astrologer(db_session, seeded_astrologer):
    # A seeded astrologer with no user_id at all (e.g. never synced/linked)
    # must never resolve — there'd be nothing to match against.
    seeded_astrologer.user_id = None
    db_session.commit()

    with pytest.raises(InvalidTokenError):
        auth_service.verify_astrologer_session(db_session, "1")
