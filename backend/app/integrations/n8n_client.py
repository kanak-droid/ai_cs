# Real integration for astrologers linked to a real expert_id; mocked
# otherwise — same split as payout_client/kyc_client/queue_performance_client,
# since the target workflow's own tracking sheet is keyed by real expert_id
# (a made-up id for an unlinked astrologer would pollute ops' real sheet).
# Has its own mock switch (N8N_MOCK_MODE), independent of the shared
# MOCK_MODE, same reasoning as SLACK_MOCK_MODE/EMAIL_MOCK_MODE.
#
# The n8n workflow ("Astro Image Enhancement") is triggered by a Form node,
# not a plain webhook, and has no "respond to caller" step at all — its only
# output is a row appended to a Google Sheet (expert_id, old image link, new
# image link). So "calling" it means: POST multipart form data to the form's
# submission URL, then poll that same sheet for a new row for this
# expert_id and read the beautified image's link out of it once it appears.
import time
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.integrations import sheets_client
from app.models.astrologer import Astrologer

_DOWNLOAD_TIMEOUT_SECONDS = 30.0
_TRIGGER_TIMEOUT_SECONDS = 30.0

# Column positions in the log sheet, left to right (Expert ID, Old Image,
# Image, New Image) — checked against the workflow's Google Sheets node.
_COL_EXPERT_ID = 0
_COL_NEW_IMAGE = 3


@dataclass(frozen=True)
class BeautifyResult:
    astrologer_id: int
    processed_image_url: str


def _download_image(image_url: str) -> tuple[bytes, str, str]:
    response = httpx.get(image_url, timeout=_DOWNLOAD_TIMEOUT_SECONDS)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "image/jpeg")
    filename = image_url.rsplit("/", 1)[-1] or "photo.jpg"
    return response.content, content_type, filename


def _trigger_workflow(expert_id: int, image_bytes: bytes, content_type: str, filename: str) -> None:
    files = {"Data": (filename, image_bytes, content_type)}
    data = {"expert id": str(expert_id)}
    response = httpx.post(
        settings.N8N_BEAUTIFY_FORM_URL, files=files, data=data, timeout=_TRIGGER_TIMEOUT_SECONDS
    )
    response.raise_for_status()


def _count_existing_rows(expert_id: int) -> int:
    _, rows = sheets_client.read_tab(
        settings.N8N_BEAUTIFY_LOG_SHEET_ID, settings.N8N_BEAUTIFY_LOG_TAB, header_row=1
    )
    return sum(1 for row in rows if sheets_client.cell(row, _COL_EXPERT_ID) == str(expert_id))


def _find_new_row(expert_id: int, rows_before: int) -> str | None:
    _, rows = sheets_client.read_tab(
        settings.N8N_BEAUTIFY_LOG_SHEET_ID, settings.N8N_BEAUTIFY_LOG_TAB, header_row=1
    )
    matching = [row for row in rows if sheets_client.cell(row, _COL_EXPERT_ID) == str(expert_id)]
    if len(matching) <= rows_before:
        return None
    # The workflow only ever appends — the newest matching row is the last one.
    return sheets_client.cell(matching[-1], _COL_NEW_IMAGE)


def _real_trigger_photo_beautify(astrologer_id: int, expert_id: int, image_url: str) -> BeautifyResult:
    rows_before = _count_existing_rows(expert_id)

    image_bytes, content_type, filename = _download_image(image_url)
    _trigger_workflow(expert_id, image_bytes, content_type, filename)

    deadline = time.monotonic() + settings.N8N_BEAUTIFY_POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(settings.N8N_BEAUTIFY_POLL_INTERVAL_SECONDS)
        found_url = _find_new_row(expert_id, rows_before)
        if found_url:
            return BeautifyResult(astrologer_id=astrologer_id, processed_image_url=found_url)

    raise TimeoutError(
        f"n8n beautify workflow for expert_id={expert_id} did not log a result within "
        f"{settings.N8N_BEAUTIFY_POLL_TIMEOUT_SECONDS}s"
    )


def trigger_photo_beautify(db, astrologer_id: int, image_url: str) -> BeautifyResult:
    astrologer = db.get(Astrologer, astrologer_id)
    if not settings.N8N_MOCK_MODE and astrologer and astrologer.expert_id:
        return _real_trigger_photo_beautify(astrologer_id, astrologer.expert_id, image_url)

    # Mock fallback — deterministic per astrologer_id/image_url so repeated
    # calls/demos/tests are stable.
    fake_url = (
        f"https://cdn.astrolokal.example/beautified/{astrologer_id}"
        f"/{abs(hash(image_url)) % 100000}.jpg"
    )
    return BeautifyResult(astrologer_id=astrologer_id, processed_image_url=fake_url)
