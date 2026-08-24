import httpx

from app.core.config import settings
from app.integrations import moengage_client
from app.services import ticket_service


def _make_ticket(db_session, seeded_astrologer):
    return ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )


def test_mock_mode_never_calls_httpx(db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "MOENGAGE_MOCK_MODE", True)

    def _boom(*args, **kwargs):
        raise AssertionError("httpx.post should never be called while MOENGAGE_MOCK_MODE is on")

    monkeypatch.setattr(httpx, "post", _boom)

    ticket = _make_ticket(db_session, seeded_astrologer)

    moengage_client.send_ticket_status_event(
        ticket, new_status="in_progress", changed_by="admin@test.example", note=None
    )


def test_skips_sending_when_astrologer_has_no_linked_user_id(db_session, seeded_astrologer, monkeypatch):
    seeded_astrologer.user_id = None
    db_session.commit()
    monkeypatch.setattr(settings, "MOENGAGE_MOCK_MODE", False)

    def _boom(*args, **kwargs):
        raise AssertionError("httpx.post should never be called with no linked user_id")

    monkeypatch.setattr(httpx, "post", _boom)

    ticket = _make_ticket(db_session, seeded_astrologer)

    moengage_client.send_ticket_status_event(
        ticket, new_status="in_progress", changed_by="admin@test.example", note=None
    )


def test_real_network_failure_is_caught_not_raised(db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "MOENGAGE_MOCK_MODE", False)
    monkeypatch.setattr(settings, "MOENGAGE_APP_ID", "test-app")
    monkeypatch.setattr(settings, "MOENGAGE_API_KEY", "test-key")

    def _raise(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", _raise)

    ticket = _make_ticket(db_session, seeded_astrologer)

    # Must not raise — a MoEngage outage can never be allowed to propagate
    # out of this function (see the caller, ticket_service._record_status).
    moengage_client.send_ticket_status_event(
        ticket, new_status="in_progress", changed_by="admin@test.example", note=None
    )
