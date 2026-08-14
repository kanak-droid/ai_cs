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


def test_parses_raw_json_from_env_var(monkeypatch):
    monkeypatch.setattr(
        settings, "GOOGLE_SHEETS_CREDENTIALS_JSON", json.dumps(_SAMPLE_CREDS)
    )

    assert sheets_client._credentials_info_from_env() == _SAMPLE_CREDS


def test_parses_base64_encoded_json_from_env_var(monkeypatch):
    encoded = base64.b64encode(json.dumps(_SAMPLE_CREDS).encode()).decode()
    monkeypatch.setattr(settings, "GOOGLE_SHEETS_CREDENTIALS_JSON", encoded)

    assert sheets_client._credentials_info_from_env() == _SAMPLE_CREDS


def test_garbage_env_var_raises_rather_than_silently_falling_back(monkeypatch):
    # Not valid JSON and not valid base64-of-JSON — should fail loudly, not
    # silently pretend the env var was never set and fall back to the file.
    monkeypatch.setattr(settings, "GOOGLE_SHEETS_CREDENTIALS_JSON", "not json and not base64!!")

    with pytest.raises(Exception):
        sheets_client._credentials_info_from_env()
