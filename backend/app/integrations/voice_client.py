# AI phone support directly on Twilio Voice + ConversationRelay — no
# third-party voice-AI platform in the loop. Twilio owns telephony, STT,
# TTS, and interruption/turn-taking (via ConversationRelay); this file only
# asks Twilio to dial out. The "brain" lives on our side: Twilio streams
# transcribed caller speech to /api/voice/conversation-relay (a WebSocket —
# see app/api/routes/voice.py), we reply with plain text, ConversationRelay
# speaks it.
#
# Has its own mock switch (VOICE_MOCK_MODE), independent of the shared
# MOCK_MODE, same reasoning as SLACK_MOCK_MODE/N8N_MOCK_MODE — going real
# needs a funded Twilio account with a real Voice-capable number, which
# doesn't exist by default.
import uuid
from dataclasses import dataclass
from urllib.parse import urlencode

from twilio.rest import Client

from app.core.config import settings


@dataclass(frozen=True)
class OutboundCallResult:
    twilio_call_sid: str
    status: str


def _real_create_call(phone_number: str, relay_token: str) -> OutboundCallResult:
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    query = urlencode({"call_token": relay_token})
    call = client.calls.create(
        to=phone_number,
        from_=settings.TWILIO_PHONE_NUMBER,
        url=f"{settings.VOICE_PUBLIC_BASE_URL}/api/voice/twiml?{query}",
        status_callback=f"{settings.VOICE_PUBLIC_BASE_URL}/api/voice/status-callback?{query}",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
    )
    return OutboundCallResult(twilio_call_sid=call.sid, status=call.status)


def create_call(phone_number: str, relay_token: str) -> OutboundCallResult:
    if not settings.VOICE_MOCK_MODE:
        return _real_create_call(phone_number, relay_token)

    # Mock fallback. A fresh id per call, not a hash of call_id alone —
    # Call.twilio_call_sid is unique, and Twilio's real CallSid format
    # ("CA" + 32 hex chars) is mimicked loosely so mock rows are
    # recognizable at a glance without being mistaken for a real one.
    return OutboundCallResult(twilio_call_sid=f"CAmock{uuid.uuid4().hex[:30]}", status="queued")
