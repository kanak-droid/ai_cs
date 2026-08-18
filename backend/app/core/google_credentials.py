"""Shared parsing for a Google service-account JSON credential passed via an
env var (as opposed to a file on disk) — extracted from sheets_client.py
after the exact same class of bug hit THREE separate times in production
for the Google Sheets credential specifically: Devtron's Secret editor
silently rewriting pasted JSON into native YAML, trailing base64 "="
padding getting stripped, and a value starting with "{" getting wrapped in
literal quote characters. Anything else that passes a Google service-account
JSON through an env var (e.g. the Gemini Vertex AI client) is exposed to
the identical failure modes, so it gets the identical defensive parsing
rather than relearning each one from a fresh production incident.
"""

import base64
import json

import yaml


def parse_service_account_json(raw: str) -> dict | None:
    """None if `raw` is blank (env var unset). Raises if it's set but isn't
    valid JSON, YAML, or base64-encoded JSON of a mapping — fails loudly
    rather than silently falling back to some other credential source."""
    raw = raw.strip()
    if not raw:
        return None
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        raw = raw[1:-1].strip()
    parsed = yaml.safe_load(raw)
    if isinstance(parsed, dict):
        return parsed
    padded = raw + "=" * (-len(raw) % 4)
    return json.loads(base64.b64decode(padded).decode("utf-8"))
