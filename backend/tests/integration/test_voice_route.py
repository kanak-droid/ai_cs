import base64
import hashlib
import hmac

from app.core.config import settings
from app.models.call import Call
from app.models.enums import CallStatus
from tests.unit.test_agent_tool_selection import FakeAgentClient, text_response

_SECRET = "test-webhook-secret"
_AUTH_TOKEN = "test-twilio-auth-token"


def _sign(url: str, params: dict) -> str:
    """Reimplements Twilio's own request-signing algorithm (HMAC-SHA1 over
    the URL plus each POST param's key+value, sorted by key, base64
    encoded) purely to construct a validly-signed test request — the
    production code under test (app.api.routes.voice._check_twilio_signature)
    verifies via the official `twilio` SDK's RequestValidator, not this.
    See https://www.twilio.com/docs/usage/webhooks/webhooks-security.
    """
    body = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    mac = hmac.new(_AUTH_TOKEN.encode(), body.encode(), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode()


def _seed_call(db_session, seeded_astrologer, twilio_call_sid="CA" + "0" * 32):
    call = Call(
        astrologer_id=seeded_astrologer.id,
        phone_number=seeded_astrologer.phone,
        twilio_call_sid=twilio_call_sid,
        status=CallStatus.IN_PROGRESS,
    )
    db_session.add(call)
    db_session.commit()
    return call


def test_request_call_requires_auth(client):
    response = client.post("/api/voice/request-call", json={})
    assert response.status_code in (401, 403)


def test_request_call_creates_a_queued_call(client, db_session, seeded_astrologer, astrologer_auth_header):
    response = client.post(
        "/api/voice/request-call", json={"session_id": "sess-1"}, headers=astrologer_auth_header
    )

    assert response.status_code == 200
    body = response.json()
    call = db_session.get(Call, body["call_id"])
    assert call.astrologer_id == seeded_astrologer.id
    assert call.phone_number == seeded_astrologer.phone
    assert call.session_id == "sess-1"
    assert call.twilio_call_sid is not None  # mocked, but always set
    assert call.status == CallStatus.QUEUED


def test_twiml_rejects_wrong_secret(client, db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_WEBHOOK_SECRET", _SECRET)
    call = _seed_call(db_session, seeded_astrologer)

    response = client.post(f"/api/voice/twiml?call_id={call.id}&secret=wrong")

    assert response.status_code == 403


def test_twiml_rejects_bad_signature(client, db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_WEBHOOK_SECRET", _SECRET)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", _AUTH_TOKEN)
    call = _seed_call(db_session, seeded_astrologer)

    response = client.post(
        f"/api/voice/twiml?call_id={call.id}&secret={_SECRET}",
        headers={"X-Twilio-Signature": "not-a-real-signature"},
    )

    assert response.status_code == 403


def test_twiml_returns_conversation_relay_xml_for_a_validly_signed_request(
    client, db_session, seeded_astrologer, monkeypatch
):
    monkeypatch.setattr(settings, "TWILIO_WEBHOOK_SECRET", _SECRET)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", _AUTH_TOKEN)
    monkeypatch.setattr(settings, "VOICE_PUBLIC_BASE_URL", "https://example.ngrok-free.app")
    call = _seed_call(db_session, seeded_astrologer)

    url_path = f"/api/voice/twiml?call_id={call.id}&secret={_SECRET}"
    full_url = f"https://example.ngrok-free.app{url_path}"
    signature = _sign(full_url, {})

    response = client.post(url_path, headers={"X-Twilio-Signature": signature})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<ConversationRelay" in response.text
    assert f'value="{call.id}"' in response.text
    assert "wss://example.ngrok-free.app" in response.text


def test_status_callback_marks_call_ended(client, db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_WEBHOOK_SECRET", _SECRET)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", _AUTH_TOKEN)
    monkeypatch.setattr(settings, "VOICE_PUBLIC_BASE_URL", "https://example.ngrok-free.app")
    call = _seed_call(db_session, seeded_astrologer)

    url_path = f"/api/voice/status-callback?call_id={call.id}&secret={_SECRET}"
    full_url = f"https://example.ngrok-free.app{url_path}"
    form = {"CallStatus": "completed", "CallSid": call.twilio_call_sid}
    signature = _sign(full_url, form)

    response = client.post(url_path, data=form, headers={"X-Twilio-Signature": signature})

    assert response.status_code == 200
    db_session.refresh(call)
    assert call.status == CallStatus.ENDED
    assert call.ended_at is not None


def test_conversation_relay_websocket_runs_the_same_orchestrator_as_chat(
    client, db_session, seeded_astrologer, monkeypatch
):
    monkeypatch.setattr(settings, "TWILIO_WEBHOOK_SECRET", _SECRET)
    call = _seed_call(db_session, seeded_astrologer)

    fake_client = FakeAgentClient([text_response("Your payout is scheduled for the 5th.")])
    monkeypatch.setattr("app.services.call_service.get_voice_agent_client", lambda: fake_client)

    with client.websocket_connect(f"/api/voice/conversation-relay?call_id={call.id}&secret={_SECRET}") as ws:
        ws.send_json(
            {
                "type": "setup",
                "callSid": call.twilio_call_sid,
                "customParameters": {"call_id": str(call.id)},
            }
        )
        ws.send_json({"type": "prompt", "voicePrompt": "What is my payout status?", "last": True})
        reply = ws.receive_json()

    assert reply == {"type": "text", "token": "Your payout is scheduled for the 5th.", "last": True}

    db_session.refresh(call)
    assert "What is my payout status?" in call.transcript
    assert "Your payout is scheduled for the 5th." in call.transcript


def test_conversation_relay_websocket_rejects_wrong_secret(client, db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_WEBHOOK_SECRET", _SECRET)
    call = _seed_call(db_session, seeded_astrologer)

    from starlette.websockets import WebSocketDisconnect

    try:
        with client.websocket_connect(f"/api/voice/conversation-relay?call_id={call.id}&secret=wrong"):
            raised = False
    except WebSocketDisconnect:
        raised = True

    assert raised
