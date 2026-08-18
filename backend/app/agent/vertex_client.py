"""Builds an authenticated Gemini client against Vertex AI, shared by the
main chat loop (client.py) and the one-shot screenshot-analysis call
(vision.py) so both authenticate the same way.

Switched from the plain Gemini Developer API (an API key) to Vertex AI
2026-08-18 — per ops, production should no longer use a bare Gemini API
key, and billing needs to be attributable per request (see the `labels`
each call site passes into GenerateContentConfig). Vertex AI uses a GCP
service account instead of an API key, authenticated the same
credentials-from-JSON way as the Google Sheets service account (and reusing
its exact defensive env-var parsing — see google_credentials.py).
"""

from google import genai
from google.oauth2 import service_account

from app.core.config import settings
from app.core.google_credentials import parse_service_account_json

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def build_vertex_client() -> genai.Client:
    info = parse_service_account_json(settings.GEMINI_VERTEX_CREDENTIALS_JSON)
    if info is None:
        raise RuntimeError(
            "GEMINI_VERTEX_CREDENTIALS_JSON is not set — required now that Gemini access goes "
            "through Vertex AI (a GCP service account) instead of a plain API key."
        )
    credentials = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
    return genai.Client(
        vertexai=True,
        # Read straight off the credential itself (per the org's migration
        # guide) rather than a separately-configured setting — one less
        # value to keep in sync, and it can never drift from whichever
        # project the credentials actually belong to.
        project=info["project_id"],
        location=settings.GOOGLE_CLOUD_LOCATION,
        credentials=credentials,
    )


def billing_labels() -> dict[str, str]:
    """The org-wide label every Gemini call must carry (shared migration
    guide, 2026-08-18): key "billing_category", value
    "{environment}_{feature}", all lowercase, underscore-joined — e.g.
    "production_supply_help". Same value for every call site in this
    codebase (chat loop, screenshot analysis) rather than a finer per-flow
    breakdown, since the shared format is explicitly just these two parts.
    """
    return {"billing_category": f"{settings.ENVIRONMENT}_{settings.GEMINI_BILLING_FEATURE}"}
