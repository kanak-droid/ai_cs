import pytest

from app.agent import vertex_client
from app.core.config import settings


def test_build_vertex_client_raises_when_credentials_are_missing(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_VERTEX_CREDENTIALS_JSON", "")

    with pytest.raises(RuntimeError):
        vertex_client.build_vertex_client()


def test_build_vertex_client_wires_project_location_and_credentials(monkeypatch):
    monkeypatch.setattr(
        settings, "GEMINI_VERTEX_CREDENTIALS_JSON", '{"type": "service_account"}'
    )
    monkeypatch.setattr(settings, "GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setattr(settings, "GOOGLE_CLOUD_LOCATION", "asia-south1")

    fake_credentials = object()
    monkeypatch.setattr(
        vertex_client.service_account.Credentials,
        "from_service_account_info",
        lambda info, scopes: fake_credentials,
    )
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(vertex_client.genai, "Client", FakeClient)

    client = vertex_client.build_vertex_client()

    assert isinstance(client, FakeClient)
    assert captured == {
        "vertexai": True,
        "project": "test-project",
        "location": "asia-south1",
        "credentials": fake_credentials,
    }


def test_billing_labels_follow_the_shared_environment_feature_format(monkeypatch):
    # Org-wide convention (2026-08-18): key "billing_category", value
    # "{environment}_{feature}", lowercase, underscore-joined — e.g.
    # "production_supply_help". Same for every call site in this codebase.
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "GEMINI_BILLING_FEATURE", "supply_help")

    assert vertex_client.billing_labels() == {"billing_category": "production_supply_help"}
