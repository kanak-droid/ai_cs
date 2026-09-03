# AI phone support via Vapi (https://vapi.ai). Vapi owns the phone number,
# telephony, STT, TTS, and interruption/turn-taking — we only (a) ask it to
# dial out, via this file, and (b) supply the "brain" for each turn, via
# app/api/routes/voice.py's Custom LLM endpoint, which vapi_call_id below
# lets us route back to the right astrologer/Call row.
#
# Has its own mock switch (VOICE_MOCK_MODE), independent of the shared
# MOCK_MODE, same reasoning as SLACK_MOCK_MODE/N8N_MOCK_MODE — going real
# needs a funded Vapi account + a phone number + an assistant configured
# with a Custom LLM model pointed at {VOICE_PUBLIC_BASE_URL}/api/voice/
# custom-llm, none of which exist yet.
import uuid
from dataclasses import dataclass

import httpx

from app.core.config import settings

_VAPI_BASE_URL = "https://api.vapi.ai"
_REQUEST_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class OutboundCallResult:
    vapi_call_id: str
    status: str


def _real_create_call(phone_number: str) -> OutboundCallResult:
    response = httpx.post(
        f"{_VAPI_BASE_URL}/call",
        headers={"Authorization": f"Bearer {settings.VAPI_API_KEY}"},
        json={
            "assistantId": settings.VAPI_ASSISTANT_ID,
            "phoneNumberId": settings.VAPI_PHONE_NUMBER_ID,
            "customer": {"number": phone_number},
        },
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    body = response.json()
    return OutboundCallResult(vapi_call_id=body["id"], status=body.get("status", "queued"))


def create_call(phone_number: str, astrologer_id: int) -> OutboundCallResult:
    if not settings.VOICE_MOCK_MODE:
        return _real_create_call(phone_number)

    # Mock fallback. Unlike n8n_client's fake URL, this can't be a
    # deterministic hash of astrologer_id alone — Call.vapi_call_id is
    # unique, and the same astrologer requesting a second demo call would
    # collide — so it's a fresh id per call, still clearly marked as mock.
    return OutboundCallResult(vapi_call_id=f"mock-call-{astrologer_id}-{uuid.uuid4().hex[:8]}", status="queued")
