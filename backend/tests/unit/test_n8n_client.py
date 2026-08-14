import time

import pytest

from app.core.config import settings
from app.integrations import n8n_client, sheets_client
from app.models.astrologer import Astrologer


def _linked_astrologer(db_session, expert_id: int) -> Astrologer:
    astrologer = Astrologer(name="Linked", phone="+91-1", language="Hindi", expert_id=expert_id)
    db_session.add(astrologer)
    db_session.commit()
    return astrologer


def test_unlinked_astrologer_always_gets_the_mock(db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "N8N_MOCK_MODE", False)

    result = n8n_client.trigger_photo_beautify(db_session, seeded_astrologer.id, "http://x/photo.jpg")

    assert result.astrologer_id == seeded_astrologer.id
    assert "beautified" in result.processed_image_url


def test_n8n_mock_mode_skips_real_even_when_linked(db_session, monkeypatch):
    astrologer = _linked_astrologer(db_session, expert_id=900)
    monkeypatch.setattr(settings, "N8N_MOCK_MODE", True)

    def _boom(*args, **kwargs):
        raise AssertionError("real path must not run under N8N_MOCK_MODE")

    monkeypatch.setattr(n8n_client, "_real_trigger_photo_beautify", _boom)

    result = n8n_client.trigger_photo_beautify(db_session, astrologer.id, "http://x/photo.jpg")

    assert "beautified" in result.processed_image_url


def test_linked_astrologer_with_mock_mode_off_uses_the_real_path(db_session, monkeypatch):
    astrologer = _linked_astrologer(db_session, expert_id=901)
    monkeypatch.setattr(settings, "N8N_MOCK_MODE", False)

    called = {}

    def fake_real(astrologer_id, expert_id, image_url):
        called["args"] = (astrologer_id, expert_id, image_url)
        return n8n_client.BeautifyResult(astrologer_id=astrologer_id, processed_image_url="http://real/x.jpg")

    monkeypatch.setattr(n8n_client, "_real_trigger_photo_beautify", fake_real)

    result = n8n_client.trigger_photo_beautify(db_session, astrologer.id, "http://x/photo.jpg")

    assert called["args"] == (astrologer.id, 901, "http://x/photo.jpg")
    assert result.processed_image_url == "http://real/x.jpg"


def test_count_existing_rows_matches_by_expert_id_column(monkeypatch):
    header = ["Expert ID", "Old Image", "Image", "New Image"]
    rows = [["901", "old1", "", "new1"], ["902", "old2", "", "new2"], ["901", "old3", "", "new3"]]
    monkeypatch.setattr(sheets_client, "read_tab", lambda *a, **k: (header, rows))

    assert n8n_client._count_existing_rows(901) == 2
    assert n8n_client._count_existing_rows(902) == 1
    assert n8n_client._count_existing_rows(999) == 0


def test_find_new_row_returns_none_until_a_row_is_added(monkeypatch):
    header = ["Expert ID", "Old Image", "Image", "New Image"]
    rows = [["901", "old1", "", "new1"]]
    monkeypatch.setattr(sheets_client, "read_tab", lambda *a, **k: (header, rows))

    assert n8n_client._find_new_row(901, rows_before=1) is None

    rows.append(["901", "old2", "", "new2"])
    assert n8n_client._find_new_row(901, rows_before=1) == "new2"


def test_real_trigger_polls_until_the_row_appears(monkeypatch):
    monkeypatch.setattr(settings, "N8N_BEAUTIFY_POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(settings, "N8N_BEAUTIFY_POLL_TIMEOUT_SECONDS", 10)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    monkeypatch.setattr(n8n_client, "_count_existing_rows", lambda expert_id: 0)
    monkeypatch.setattr(
        n8n_client, "_download_image", lambda url: (b"bytes", "image/jpeg", "photo.jpg")
    )
    monkeypatch.setattr(n8n_client, "_trigger_workflow", lambda *a, **k: None)

    poll_results = iter([None, None, "http://drive/new.jpg"])
    monkeypatch.setattr(n8n_client, "_find_new_row", lambda expert_id, rows_before: next(poll_results))

    result = n8n_client._real_trigger_photo_beautify(
        astrologer_id=5, expert_id=901, image_url="http://x/photo.jpg"
    )

    assert result.processed_image_url == "http://drive/new.jpg"


def test_real_trigger_raises_timeout_error_when_no_row_ever_appears(monkeypatch):
    monkeypatch.setattr(settings, "N8N_BEAUTIFY_POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(settings, "N8N_BEAUTIFY_POLL_TIMEOUT_SECONDS", 0)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    monkeypatch.setattr(n8n_client, "_count_existing_rows", lambda expert_id: 0)
    monkeypatch.setattr(
        n8n_client, "_download_image", lambda url: (b"bytes", "image/jpeg", "photo.jpg")
    )
    monkeypatch.setattr(n8n_client, "_trigger_workflow", lambda *a, **k: None)
    monkeypatch.setattr(n8n_client, "_find_new_row", lambda expert_id, rows_before: None)

    with pytest.raises(TimeoutError):
        n8n_client._real_trigger_photo_beautify(astrologer_id=5, expert_id=901, image_url="http://x/photo.jpg")
