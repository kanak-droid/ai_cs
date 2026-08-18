import httpx

from app.core.config import settings
from app.integrations import object_storage, slack_client
from app.models.slack_log import SlackLog


class _FakeResponse:
    def __init__(self, json_data=None, content=b"", status_code=200):
        self._json = json_data or {}
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json


def test_mock_mode_logs_without_any_network_call(db_session, monkeypatch):
    monkeypatch.setattr(settings, "SLACK_MOCK_MODE", True)

    def _boom(*args, **kwargs):
        raise AssertionError("must not touch the network in mock mode")

    monkeypatch.setattr(httpx, "get", _boom)
    monkeypatch.setattr(httpx, "post", _boom)

    slack_client.upload_attachment(db_session, attachment_url="http://x/photo.jpg", ticket_id=None)

    entry = db_session.query(SlackLog).filter_by(ticket_id=None).one()
    assert entry.mock is True
    assert "photo.jpg" in entry.message


def test_real_upload_success_writes_a_non_mock_log(db_session, monkeypatch):
    monkeypatch.setattr(settings, "SLACK_MOCK_MODE", False)
    monkeypatch.setattr(settings, "SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setattr(settings, "SLACK_UPLOAD_CHANNEL_ID", "C123")

    calls = []

    # Fetches the actual bytes via object_storage (our own AWS credentials
    # for S3, see its docstring) rather than a plain httpx.get against the
    # attachment's URL — a raw unauthenticated GET 403s on S3 unless the
    # bucket has a public-read policy attached (confirmed live 2026-08-18).
    monkeypatch.setattr(
        object_storage, "download_file", lambda url: (b"fake-bytes", "image/jpeg")
    )

    def fake_post(url, **kwargs):
        calls.append(("post", url))
        if "getUploadURLExternal" in url:
            return _FakeResponse({"ok": True, "upload_url": "https://upload.slack.com/x", "file_id": "F1"})
        if "upload.slack.com" in url:
            return _FakeResponse({})
        if "completeUploadExternal" in url:
            return _FakeResponse({"ok": True})
        raise AssertionError(f"unexpected POST to {url}")

    monkeypatch.setattr(httpx, "post", fake_post)

    slack_client.upload_attachment(db_session, attachment_url="http://x/photo.jpg", ticket_id=None)

    entry = db_session.query(SlackLog).filter_by(ticket_id=None).one()
    assert entry.mock is False
    assert entry.channel == "C123"
    # All 3 real Slack API steps happened, in order.
    assert [c[0] for c in calls] == ["post", "post", "post"]


def test_real_upload_failure_is_swallowed_not_raised(db_session, monkeypatch):
    # Best-effort: a failure to fetch the file must never bubble up into
    # create_ticket() and break ticket creation for the astrologer.
    monkeypatch.setattr(settings, "SLACK_MOCK_MODE", False)
    monkeypatch.setattr(settings, "SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setattr(settings, "SLACK_UPLOAD_CHANNEL_ID", "C123")

    def failing_download(url):
        raise RuntimeError("boom")

    monkeypatch.setattr(object_storage, "download_file", failing_download)

    slack_client.upload_attachment(db_session, attachment_url="http://x/photo.jpg", ticket_id=None)

    # No log row written on failure, and — the real assertion — no exception.
    assert db_session.query(SlackLog).filter_by(ticket_id=None).count() == 0


def test_slack_api_error_response_is_also_swallowed(db_session, monkeypatch):
    monkeypatch.setattr(settings, "SLACK_MOCK_MODE", False)
    monkeypatch.setattr(settings, "SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setattr(settings, "SLACK_UPLOAD_CHANNEL_ID", "C123")

    monkeypatch.setattr(object_storage, "download_file", lambda url: (b"bytes", "image/jpeg"))
    monkeypatch.setattr(
        httpx, "post", lambda url, **kwargs: _FakeResponse({"ok": False, "error": "not_in_channel"})
    )

    slack_client.upload_attachment(db_session, attachment_url="http://x/photo.jpg", ticket_id=None)

    assert db_session.query(SlackLog).filter_by(ticket_id=None).count() == 0
