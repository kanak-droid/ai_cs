import httpx
import pytest

from app.core.config import settings
from app.integrations import object_storage, queue_performance_client, zoho_client
from app.integrations.queue_performance_client import QueuePerformance
from app.models.admin import Admin
from app.models.enums import AdminRole, TicketStatus
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


def test_zoho_status_for_terminal_status_wins_over_escalated():
    # Regression: an escalated ticket that later gets resolved must show
    # "Closed" in Zoho, not stay stuck showing "Escalated" forever just
    # because it was escalated at some earlier point in its life.
    class _FakeTicket:
        escalated_to_kam = True

    for status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
        ticket = _FakeTicket()
        ticket.status = status
        assert zoho_client.zoho_status_for(ticket) == "Closed"


def test_zoho_category_for_maps_known_categories():
    assert zoho_client._zoho_category_for("payout") == "Payment Queries"
    assert zoho_client._zoho_category_for("kyc") == "Withdrawal / KYC"
    assert zoho_client._zoho_category_for("no_visibility") == "Low Visibility"


def test_zoho_category_for_falls_back_for_unknown_category():
    assert zoho_client._zoho_category_for("something_new") == "User Queries"


def test_zoho_sub_issue_for_matches_keywords_case_insensitively():
    assert zoho_client._zoho_sub_issue_for("Payout_Delay") == "Withdrawal Amount not Received"
    assert zoho_client._zoho_sub_issue_for("app_crash") == "Tech Issues"
    assert zoho_client._zoho_sub_issue_for("low_calls") == "Low Visibility"


def test_zoho_sub_issue_for_falls_back_to_general_inquiry():
    assert zoho_client._zoho_sub_issue_for("something_unrelated") == "General Inquiry"
    assert zoho_client._zoho_sub_issue_for(None) == "General Inquiry"


def test_zoho_language_for_uses_the_assigned_cs_language(db_session, seeded_astrologer):
    cs = Admin(name="Tamil CS", email="tamil-cs@test.example", role=AdminRole.CS, languages=["Tamil"])
    db_session.add(cs)
    db_session.commit()
    ticket = _make_ticket(db_session, seeded_astrologer)
    ticket.assigned_cs_id = cs.id
    db_session.commit()
    db_session.refresh(ticket)

    assert zoho_client._zoho_language_for(ticket) == "Tamil"


def test_zoho_language_for_falls_back_when_cs_language_not_in_zoho_list(db_session, seeded_astrologer):
    cs = Admin(
        name="English CS", email="english-cs@test.example", role=AdminRole.CS, languages=["English"]
    )
    db_session.add(cs)
    db_session.commit()
    ticket = _make_ticket(db_session, seeded_astrologer)
    ticket.assigned_cs_id = cs.id
    db_session.commit()
    db_session.refresh(ticket)

    assert zoho_client._zoho_language_for(ticket) == "Hindi"


def test_zoho_language_for_falls_back_with_no_assigned_cs(db_session, seeded_astrologer):
    ticket = _make_ticket(db_session, seeded_astrologer)
    ticket.assigned_cs_id = None
    db_session.commit()
    db_session.refresh(ticket)

    assert zoho_client._zoho_language_for(ticket) == "Hindi"


def test_mock_mode_never_calls_httpx(db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", True)

    def _boom(*args, **kwargs):
        raise AssertionError("httpx should never be called while ZOHO_MOCK_MODE is on")

    monkeypatch.setattr(httpx, "post", _boom)
    monkeypatch.setattr(httpx, "patch", _boom)

    ticket = _make_ticket(db_session, seeded_astrologer)

    zoho_id = zoho_client.create_ticket(db_session, ticket)
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
    assert zoho_client.create_ticket(db_session, ticket) is None


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


def test_create_ticket_includes_the_required_layout_fields(db_session, seeded_astrologer, monkeypatch):
    ticket = _make_ticket(db_session, seeded_astrologer)

    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)
    monkeypatch.setattr(zoho_client, "_get_access_token", lambda: "fake-token")
    monkeypatch.setattr(zoho_client, "find_agent_id_by_email", lambda email: None)

    captured = {}

    def _fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        return _FakeResponse({"id": "zoho-1"})

    monkeypatch.setattr(httpx, "post", _fake_post)

    zoho_client.create_ticket(db_session, ticket)

    payload = captured["json"]
    assert payload["category"] == "User Queries"  # ticket's category is "other"
    assert payload["language"] == "Hindi"  # no assigned CS in this test -> fallback
    assert payload["channel"] == "Chat"
    assert payload["cf"] == {
        "cf_user_type": "Astrologer",
        "cf_sub_status": "RNR 1",
        "cf_sub_issue": "General Inquiry",  # sub_category is "general" -> no keyword match
        "cf_comments": "Raised via AstroHelp chatbot",
    }


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

    zoho_id = zoho_client.create_ticket(db_session, ticket)

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

    zoho_client.create_ticket(db_session, ticket)

    assert "assigneeId" not in captured["json"]


def test_create_ticket_includes_the_astrologers_priority_in_the_subject(
    db_session, seeded_astrologer, monkeypatch
):
    monkeypatch.setattr(
        queue_performance_client,
        "get_queue_performance",
        lambda db, astrologer_id: QueuePerformance(
            astrologer_id=astrologer_id, priority=2, users_connected=0, queues_connected=0,
            total_talktime_min=0,
        ),
    )
    ticket = _make_ticket(db_session, seeded_astrologer)

    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)
    monkeypatch.setattr(zoho_client, "_get_access_token", lambda: "fake-token")
    monkeypatch.setattr(zoho_client, "find_agent_id_by_email", lambda email: None)

    captured = {}

    def _fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        return _FakeResponse({"id": "zoho-1"})

    monkeypatch.setattr(httpx, "post", _fake_post)

    zoho_client.create_ticket(db_session, ticket)

    assert captured["json"]["subject"].startswith("(P2)")


def test_create_ticket_labels_unranked_astrologers_in_the_subject(
    db_session, seeded_astrologer, monkeypatch
):
    monkeypatch.setattr(
        queue_performance_client,
        "get_queue_performance",
        lambda db, astrologer_id: QueuePerformance(
            astrologer_id=astrologer_id, priority=None, users_connected=0, queues_connected=0,
            total_talktime_min=0,
        ),
    )
    ticket = _make_ticket(db_session, seeded_astrologer)

    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)
    monkeypatch.setattr(zoho_client, "_get_access_token", lambda: "fake-token")
    monkeypatch.setattr(zoho_client, "find_agent_id_by_email", lambda email: None)

    captured = {}

    def _fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        return _FakeResponse({"id": "zoho-1"})

    monkeypatch.setattr(httpx, "post", _fake_post)

    zoho_client.create_ticket(db_session, ticket)

    assert captured["json"]["subject"].startswith("(Unranked)")


def test_create_ticket_priority_lookup_failure_never_blocks_ticket_creation(
    db_session, seeded_astrologer, monkeypatch
):
    ticket = _make_ticket(db_session, seeded_astrologer)

    def _boom(db, astrologer_id):
        raise RuntimeError("priority sheet is unreachable")

    monkeypatch.setattr(queue_performance_client, "get_queue_performance", _boom)
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)
    monkeypatch.setattr(zoho_client, "_get_access_token", lambda: "fake-token")
    monkeypatch.setattr(zoho_client, "find_agent_id_by_email", lambda email: None)

    captured = {}

    def _fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        return _FakeResponse({"id": "zoho-1"})

    monkeypatch.setattr(httpx, "post", _fake_post)

    zoho_id = zoho_client.create_ticket(db_session, ticket)

    assert zoho_id == "zoho-1"
    assert captured["json"]["subject"].startswith("(Unranked)")


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


def test_post_comment_mock_mode_never_calls_httpx(monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", True)

    def _boom(*args, **kwargs):
        raise AssertionError("httpx should never be called while ZOHO_MOCK_MODE is on")

    monkeypatch.setattr(httpx, "post", _boom)

    zoho_client.post_comment("zoho-1", "Astrologer: hi\n\nAssistant: hello")


def test_post_comment_sends_the_transcript_as_a_private_comment(monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)
    monkeypatch.setattr(zoho_client, "_get_access_token", lambda: "fake-token")

    captured = {}

    def _fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return _FakeResponse({"id": "comment-1"})

    monkeypatch.setattr(httpx, "post", _fake_post)

    zoho_client.post_comment("zoho-1", "Astrologer: hi\n\nAssistant: hello")

    assert captured["url"] == "https://desk.zoho.in/api/v1/tickets/zoho-1/comments"
    assert captured["json"] == {
        "content": "Astrologer: hi\n\nAssistant: hello",
        "contentType": "plainText",
        "isPublic": False,
    }


def test_post_comment_failure_is_caught_not_raised(monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_MOCK_MODE", False)
    monkeypatch.setattr(zoho_client, "_get_access_token", lambda: "fake-token")

    def _boom(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", _boom)

    # Must not raise.
    zoho_client.post_comment("zoho-1", "some transcript")
