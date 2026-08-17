import base64
import json

import pytest

from app.core.config import settings
from app.integrations import sheets_client

_SAMPLE_CREDS = {
    "type": "service_account",
    "project_id": "x",
    "client_email": "x@x.iam.gserviceaccount.com",
}


def test_returns_none_when_env_var_unset(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_SHEETS_CREDENTIALS_JSON", "")

    assert sheets_client._credentials_info_from_env() is None


def test_parses_devtrons_yaml_rewrite_of_a_pasted_json_value(monkeypatch):
    # Hit for real in production (2026-08-18) — Devtron's Secret editor
    # silently rewrote a pasted JSON credentials value into native YAML
    # mapping syntax on save, including a literal block scalar ("private_key: |")
    # for the multi-line PEM key. Not valid JSON, not valid base64 — only a
    # YAML parser (which JSON is a subset of) handles both forms at once.
    yaml_form = (
        "type: service_account\n"
        "project_id: x\n"
        "private_key: |\n"
        "  -----BEGIN PRIVATE KEY-----\n"
        "  abc123\n"
        "  -----END PRIVATE KEY-----\n"
        "client_email: x@x.iam.gserviceaccount.com\n"
    )
    monkeypatch.setattr(settings, "GOOGLE_SHEETS_CREDENTIALS_JSON", yaml_form)

    info = sheets_client._credentials_info_from_env()

    assert info["type"] == "service_account"
    assert info["client_email"] == "x@x.iam.gserviceaccount.com"
    assert info["private_key"] == "-----BEGIN PRIVATE KEY-----\nabc123\n-----END PRIVATE KEY-----\n"


def test_parses_raw_json_from_env_var(monkeypatch):
    monkeypatch.setattr(
        settings, "GOOGLE_SHEETS_CREDENTIALS_JSON", json.dumps(_SAMPLE_CREDS)
    )

    assert sheets_client._credentials_info_from_env() == _SAMPLE_CREDS


def test_parses_raw_json_wrapped_in_quotes_by_a_yaml_editor(monkeypatch):
    # Hit for real in production (2026-08-17) — a YAML-backed Secret editor
    # wraps a value starting with "{" in quotes (unquoted "{" starts a YAML
    # flow mapping); if those literal quotes end up in the env var itself,
    # the value no longer starts with "{" and was wrongly treated as base64.
    for quote in ("'", '"'):
        wrapped = f"{quote}{json.dumps(_SAMPLE_CREDS)}{quote}"
        monkeypatch.setattr(settings, "GOOGLE_SHEETS_CREDENTIALS_JSON", wrapped)
        assert sheets_client._credentials_info_from_env() == _SAMPLE_CREDS


def test_parses_base64_encoded_json_from_env_var(monkeypatch):
    encoded = base64.b64encode(json.dumps(_SAMPLE_CREDS).encode()).decode()
    monkeypatch.setattr(settings, "GOOGLE_SHEETS_CREDENTIALS_JSON", encoded)

    assert sheets_client._credentials_info_from_env() == _SAMPLE_CREDS


def test_parses_base64_with_stripped_trailing_padding(monkeypatch):
    # Hit for real in production (2026-08-17) — trailing "=" padding got
    # silently stripped when pasted through a Secret-editing UI, twice in a
    # row. Base64 padding is always 0, 1, or 2 "=" chars — test stripping
    # each amount that was actually present.
    encoded = base64.b64encode(json.dumps(_SAMPLE_CREDS).encode()).decode()
    padding = len(encoded) - len(encoded.rstrip("="))
    for missing in range(1, padding + 1):
        stripped = encoded[:-missing]
        monkeypatch.setattr(settings, "GOOGLE_SHEETS_CREDENTIALS_JSON", stripped)
        assert sheets_client._credentials_info_from_env() == _SAMPLE_CREDS


def test_garbage_env_var_raises_rather_than_silently_falling_back(monkeypatch):
    # Not valid JSON and not valid base64-of-JSON — should fail loudly, not
    # silently pretend the env var was never set and fall back to the file.
    monkeypatch.setattr(settings, "GOOGLE_SHEETS_CREDENTIALS_JSON", "not json and not base64!!")

    with pytest.raises(Exception):
        sheets_client._credentials_info_from_env()
