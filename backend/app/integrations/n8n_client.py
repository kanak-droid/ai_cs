# MOCKED — replace with real API call.
#
# Real integration: n8n hosts a webhook workflow that runs the astrologer's
# uploaded photo through a beautify/retouch pipeline and returns the processed
# image's URL. The real call is already written below (httpx.post(...)); it's
# just never reached while MOCK_MODE is on. To go live: set MOCK_MODE=false and
# N8N_BEAUTIFY_WEBHOOK_URL to the real workflow URL — no other code changes.
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.integrations.config import MOCK_MODE


@dataclass(frozen=True)
class BeautifyResult:
    astrologer_id: int
    processed_image_url: str


def trigger_photo_beautify(astrologer_id: int, image_url: str) -> BeautifyResult:
    if MOCK_MODE:
        fake_url = (
            f"https://cdn.astrolokal.example/beautified/{astrologer_id}"
            f"/{abs(hash(image_url)) % 100000}.jpg"
        )
        return BeautifyResult(astrologer_id=astrologer_id, processed_image_url=fake_url)

    response = httpx.post(
        settings.N8N_BEAUTIFY_WEBHOOK_URL,
        json={"astrologer_id": astrologer_id, "image_url": image_url},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    return BeautifyResult(astrologer_id=astrologer_id, processed_image_url=data["processed_image_url"])
