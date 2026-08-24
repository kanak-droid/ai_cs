import httpx
import pytest

from app.core.config import settings
from app.integrations import object_storage, zoho_client
from app.models.enums import TicketStatus
from app.services import ticket_service


@pytest.fixture(autouse=True)
def _reset_zoho_client_caches():
    # Module-level caches (access token, agent list) must never leak
    # between tests — each test should see a cold cache, same as a fresh
    # process would.
    zoho_client._access_token = None
    zoho_client._access_token_expires_at = 0.0
    zoho_client._agents_cache = None
    zoho_client._agents_cache_expires_at = 0.0


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._json_data


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


def test_zoho_status_for_maps_active_statuses_to_open():
    for status in (
        TicketStatus.SUBMITTED,
        TicketStatus.ASSIGNED_TO_KAM,
        TicketStatus.UNDER_REVIEW,
        TicketStatus.IN_PROGRESS,
    ):

        class _FakeTicket:
            escalated_to_kam = False

        ticket = _FakeTicket()
        ticket.status = status
        assert zoho_client.zoho_status_for(ticket) == "Open"


def test_zoho_status_for_maps_resolved_and_closed_to_closed():
    class _FakeTicket:
        escalated_to_kam = False

    for status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
        ticket = _FakeTicket()
        ticket.status = status
        assert zoho_client.zoho_status_for(ticket) == "Closed"


def test_zoho_status_for_escalated_overrides_underlying_status():
    class _FakeTicket:
        escalated_to_kam = True
        status = TicketStatus.IN_PROGRESS

    assert zoho_client.zoho_status_for(_FakeTicket()) == "Escalated"


def test_mock_mode_never_calls_httpx(db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", True)

    def _boom(*args, **kwargs):
        raise AssertionError("httpx should never be called while ZOHO_MOCK_MODE is on")

    monkeypatch.setattr(httpx, "post", _boom)
    monkeypatch.setattr(httpx, "patch", _boom)

    ticket = _make_ticket(db_session, seeded_astrologer)

    zoho_id = zoho_client.create_ticket(ticket)
    assert zoho_id is not None
    zoho_client.update_status(zoho_id, "Open")


def test_real_ticket_creation_failure_is_caught_not_raised(db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)

    def _raise(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", _raise)

    ticket = _make_ticket(db_session, seeded_astrologer)

    # Must not raise — returns None instead, same "not pushed" signal as
    # any other failure (see the caller, ticket_service._maybe_push_to_zoho).
    assert zoho_client.create_ticket(ticket) is None


def test_real_status_update_failure_is_caught_not_raised(monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)

    def _raise(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "patch", _raise)
    monkeypatch.setattr(httpx, "post", _raise)

    # Must not raise.
    zoho_client.update_status("mock-1", "Closed")


def test_find_agent_id_by_email_returns_none_for_no_email():
    assert zoho_client.find_agent_id_by_email(None) is None
    assert zoho_client.find_agent_id_by_email("") is None


def test_find_agent_id_by_email_returns_none_in_mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", True)
    assert zoho_client.find_agent_id_by_email("saritha.b@getlokalapp.com") is None


def test_find_agent_id_by_email_matches_case_insensitively(monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)
    monkeypatch.setattr(
        zoho_client,
        "_get_agents",
        lambda: [{"id": "agent-1", "emailId": "Saritha.B@GetLokalApp.com"}],
    )

    assert zoho_client.find_agent_id_by_email("saritha.b@getlokalapp.com") == "agent-1"
    assert zoho_client.find_agent_id_by_email("someone.else@getlokalapp.com") is None


def test_find_agent_id_by_email_failure_is_caught_not_raised(monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)

    def _boom():
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(zoho_client, "_get_agents", _boom)

    assert zoho_client.find_agent_id_by_email("saritha.b@getlokalapp.com") is None


def test_create_ticket_includes_assignee_when_an_agent_matches(db_session, seeded_astrologer, monkeypatch):
    # Created while still in the default (mocked) mode from conftest's
    # network-isolation fixture — real mode is only flipped on afterward,
    # so this doesn't also trigger a second, real push via create_ticket's
    # own internal _maybe_push_to_zoho call.
    ticket = _make_ticket(db_session, seeded_astrologer)

    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)
    monkeypatch.setattr(zoho_client, "_get_access_token", lambda: "fake-token")
    monkeypatch.setattr(zoho_client, "find_agent_id_by_email", lambda email: "agent-42")

    captured = {}

    def _fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        return _FakeResponse({"id": "zoho-1"})

    monkeypatch.setattr(httpx, "post", _fake_post)

    zoho_id = zoho_client.create_ticket(ticket)

    assert zoho_id == "zoho-1"
    assert captured["json"]["assigneeId"] == "agent-42"


def test_create_ticket_omits_assignee_when_no_agent_matches(db_session, seeded_astrologer, monkeypatch):
    ticket = _make_ticket(db_session, seeded_astrologer)

    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)
    monkeypatch.setattr(zoho_client, "_get_access_token", lambda: "fake-token")
    monkeypatch.setattr(zoho_client, "find_agent_id_by_email", lambda email: None)

    captured = {}

    def _fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        return _FakeResponse({"id": "zoho-1"})

    monkeypatch.setattr(httpx, "post", _fake_post)

    zoho_client.create_ticket(ticket)

    assert "assigneeId" not in captured["json"]


def test_upload_attachment_mock_mode_never_calls_httpx(monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", True)

    def _boom(*args, **kwargs):
        raise AssertionError("httpx should never be called while ZOHO_MOCK_MODE is on")

    monkeypatch.setattr(httpx, "post", _boom)

    zoho_client.upload_attachment("zoho-1", "http://localhost:8000/uploads/photo.jpg")


def test_upload_attachment_sends_the_downloaded_file(monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)
    monkeypatch.setattr(zoho_client, "_get_access_token", lambda: "fake-token")
    monkeypatch.setattr(
        object_storage, "download_file", lambda url: (b"fake-bytes", "image/jpeg")
    )

    captured = {}

    def _fake_post(url, **kwargs):
        captured["url"] = url
        captured["files"] = kwargs["files"]
        return _FakeResponse({"id": "attachment-1"})

    monkeypatch.setattr(httpx, "post", _fake_post)

    zoho_client.upload_attachment("zoho-1", "http://localhost:8000/uploads/photo.jpg")

    assert captured["url"] == "https://desk.zoho.in/api/v1/tickets/zoho-1/attachments"
    filename, content, content_type = captured["files"]["file"]
    assert filename == "photo.jpg"
    assert content == b"fake-bytes"
    assert content_type == "image/jpeg"


def test_upload_attachment_failure_is_caught_not_raised(monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)
    monkeypatch.setattr(zoho_client, "_get_access_token", lambda: "fake-token")

    def _boom(url):
        raise RuntimeError("storage is down")

    monkeypatch.setattr(object_storage, "download_file", _boom)

    # Must not raise.
    zoho_client.upload_attachment("zoho-1", "http://localhost:8000/uploads/photo.jpg")
