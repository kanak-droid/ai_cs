from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

# Ensure every model is registered on Base.metadata before create_all().
from app import models  # noqa: F401,E402
from app.api.deps import get_db
from app.core.config import settings
from app.core.security import hash_password, issue_admin_token
from app.db.base import Base
from app.main import app
from app.models.admin import Admin
from app.models.astrologer import Astrologer
from app.models.enums import AdminAccessLevel


@pytest.fixture(autouse=True)
def _isolate_from_real_network(monkeypatch):
    # Whatever a developer's local .env has MOCK_MODE/SLACK_MOCK_MODE/
    # ZOHO_MOCK_MODE/MOENGAGE_MOCK_MODE set to (e.g. real Zoho Desk/Slack
    # credentials wired up for manual testing) must never leak into the
    # test suite — tests always exercise the mocked path. A blocked httpx
    # call as a backstop turns "forgot to mock this" into a loud failure
    # instead of a real network call (e.g. actually creating/mutating a
    # ticket in Zoho Desk) slipping through.
    monkeypatch.setattr(settings, "MOCK_MODE", True)
    monkeypatch.setattr(settings, "SLACK_MOCK_MODE", True)
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", True)
    monkeypatch.setattr(settings, "MOENGAGE_MOCK_MODE", True)
    monkeypatch.setattr(settings, "VOICE_MOCK_MODE", True)

    def _blocked(*args, **kwargs):
        raise RuntimeError("Real network calls are not allowed in tests.")

    monkeypatch.setattr(httpx, "post", _blocked)
    monkeypatch.setattr(httpx, "get", _blocked)
    monkeypatch.setattr(httpx, "patch", _blocked)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(settings.TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    """Real Postgres, SAVEPOINT-rollback isolation per test.

    Application code is free to call db.commit() (as app.services.ticket_service
    does) without leaking data between tests: commits only close the SAVEPOINT,
    which this fixture immediately restarts, while the outer transaction is
    rolled back at teardown.
    """
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def seeded_admin(db_session) -> Admin:
    admin = Admin(
        name="Test Admin",
        email="admin@test.example",
        password_hash=hash_password("test-password"),
        slack_channel="#test",
    )
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture()
def seeded_admin_access_admin(db_session) -> Admin:
    admin = Admin(
        name="Test Super Admin",
        email="super-admin@test.example",
        password_hash=hash_password("test-password"),
        slack_channel="#test",
        access_level=AdminAccessLevel.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture()
def seeded_astrologer(db_session, seeded_admin) -> Astrologer:
    astrologer = Astrologer(
        name="Test Astrologer",
        phone="+91-90000-00000",
        language="Hindi",
        user_id=500001,
        assigned_admin_id=seeded_admin.id,
    )
    db_session.add(astrologer)
    db_session.commit()
    return astrologer


@pytest.fixture()
def admin_auth_header(seeded_admin) -> dict:
    token = issue_admin_token(seeded_admin.id, seeded_admin.email, seeded_admin.access_level.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_access_auth_header(seeded_admin_access_admin) -> dict:
    token = issue_admin_token(
        seeded_admin_access_admin.id,
        seeded_admin_access_admin.email,
        seeded_admin_access_admin.access_level.value,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def astrologer_auth_header(seeded_astrologer) -> dict:
    # No signing on the astrologer side — the webview URL (and, here, the
    # Authorization header standing in for it) carries the plain user_id.
    return {"Authorization": f"Bearer {seeded_astrologer.user_id}"}
