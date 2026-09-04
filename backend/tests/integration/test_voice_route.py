import base64
import hashlib
import hmac
import secrets
import time

from app.core.config import settings
from app.models.call import Call
from app.models.enums import CallStatus
from app.services import call_service
from tests.unit.test_agent_tool_selection import FakeAgentClient, text_response

_AUTH_TOKEN = "test-twilio-auth-token"


class _SlowFakeAgentClient(FakeAgentClient):
    """Makes an interrupt race deterministic for the WebSocket test."""

    def generate(self, *, system, contents, tools):
        time.sleep(0.3)
        return super().generate(system=system, contents=contents, tools=tools)


def _sign(url: str, params: dict[str, str]) -> str:
    """Builds a Twilio-compatible test signature for one request."""
    body = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    mac = hmac.new(_AUTH_TOKEN.encode(), body.encode(), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode()


def _seed_call(db_session, seeded_astrologer, twilio_call_sid="CA" + "0" * 32):
    """Creates an in-progress call with a real opaque relay identifier."""
    call = Call(
        astrologer_id=seeded_astrologer.id,
        phone_number=seeded_astrologer.phone,
        twilio_call_sid=twilio_call_sid,
        relay_token=secrets.token_urlsafe(32),
        status=CallStatus.IN_PROGRESS,
    )
    db_session.add(call)
    db_session.commit()
    return call


def _relay_setup(call: Call) -> dict:
    """Returns the ConversationRelay setup payload emitted by Twilio."""
    return {
        "type": "setup",
        "callSid": call.twilio_call_sid,
        "customParameters": {"call_token": call.relay_token},
    }


def _receive_spoken_turn(ws) -> str:
    """Collects ConversationRelay's streamed text chunks until turn completion."""
    chunks = []
    while True:
        message = ws.receive_json()
        assert message["type"] == "text"
        chunks.append(message["token"])
        if message["last"]:
            return "".join(chunks)


def test_request_call_requires_auth(client):
    response = client.post("/api/voice/request-call", json={})

    assert response.status_code in (401, 403)


def test_request_call_creates_a_queued_call(
    client, db_session, seeded_astrologer, astrologer_auth_header
):
    response = client.post(
        "/api/voice/request-call", json={"session_id": "sess-1"}, headers=astrologer_auth_header
    )

    assert response.status_code == 200
    call = db_session.get(Call, response.json()["call_id"])
    assert call.astrologer_id == seeded_astrologer.id
    assert call.phone_number == seeded_astrologer.phone
    assert call.session_id == "sess-1"
    assert call.relay_token is not None
    assert call.twilio_call_sid is not None
    assert call.status == CallStatus.QUEUED


def test_twiml_rejects_an_unknown_call_token(client, monkeypatch):
    monkeypatch.setattr(settings, "VOICE_VALIDATE_TWILIO_SIGNATURE", False)

    response = client.post("/api/voice/twiml?call_token=not-a-real-token")

    assert response.status_code == 404


def test_twiml_rejects_bad_signature(client, db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", _AUTH_TOKEN)
    call = _seed_call(db_session, seeded_astrologer)

    response = client.post(
        f"/api/voice/twiml?call_token={call.relay_token}",
        headers={"X-Twilio-Signature": "not-a-real-signature"},
    )

    assert response.status_code == 403


def test_twiml_returns_conversation_relay_xml_for_a_validly_signed_request(
    client, db_session, seeded_astrologer, monkeypatch
):
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", _AUTH_TOKEN)
    monkeypatch.setattr(settings, "VOICE_PUBLIC_BASE_URL", "https://example.ngrok-free.app")
    call = _seed_call(db_session, seeded_astrologer)

    url_path = f"/api/voice/twiml?call_token={call.relay_token}"
    form = {"CallSid": call.twilio_call_sid}
    signature = _sign(f"https://example.ngrok-free.app{url_path}", form)
    response = client.post(url_path, data=form, headers={"X-Twilio-Signature": signature})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<ConversationRelay" in response.text
    assert f'value="{call.relay_token}"' in response.text
    assert "wss://example.ngrok-free.app" in response.text


def test_status_callback_marks_call_ended(client, db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", _AUTH_TOKEN)
    monkeypatch.setattr(settings, "VOICE_PUBLIC_BASE_URL", "https://example.ngrok-free.app")
    call = _seed_call(db_session, seeded_astrologer)

    url_path = f"/api/voice/status-callback?call_token={call.relay_token}"
    form = {"CallStatus": "completed", "CallSid": call.twilio_call_sid}
    signature = _sign(f"https://example.ngrok-free.app{url_path}", form)
    response = client.post(url_path, data=form, headers={"X-Twilio-Signature": signature})

    assert response.status_code == 200
    db_session.refresh(call)
    assert call.status == CallStatus.ENDED
    assert call.ended_at is not None
    assert call.support_summary is not None
    assert call.resolution_status == "not_connected"


def test_call_outcome_uses_openrouter_and_persists_dashboard_fields(
    db_session, seeded_astrologer, monkeypatch
):
    call = _seed_call(db_session, seeded_astrologer)
    call.transcript = "Astrologer: My payout is delayed.\nAgent: It is scheduled for Friday."
    call.actions_taken = [{"tool": "get_payout_status", "ok": True, "summary": "Payout found"}]
    db_session.commit()
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")

    class _SummaryClient:
        def generate_call_summary(self, *, prompt):
            assert "Payout found" in prompt
            return (
                '{"summary":"The caller asked about a delayed payout.",'
                '"resolution_status":"resolved",'
                '"suggested_solution":"Wait for the scheduled payout.",'
                '"next_action":"No follow-up needed."}'
            )

    monkeypatch.setattr(
        "app.services.call_service.get_voice_agent_client", lambda: _SummaryClient()
    )
    call_service.generate_call_outcome_summary(db_session, call)

    db_session.refresh(call)
    assert call.support_summary == "The caller asked about a delayed payout."
    assert call.resolution_status == "resolved"
    assert call.suggested_solution == "Wait for the scheduled payout."
    assert call.next_action == "No follow-up needed."
    assert call.summary_generated_at is not None


def test_conversation_relay_websocket_runs_the_same_orchestrator_as_chat(
    client, db_session, seeded_astrologer, monkeypatch
):
    monkeypatch.setattr(settings, "VOICE_VALIDATE_TWILIO_SIGNATURE", False)
    call = _seed_call(db_session, seeded_astrologer)
    fake_client = FakeAgentClient([text_response("Your payout is scheduled for the 5th.")])
    monkeypatch.setattr("app.services.call_service.get_voice_agent_client", lambda: fake_client)

    with client.websocket_connect(
        f"/api/voice/conversation-relay?call_token={call.relay_token}"
    ) as ws:
        ws.send_json(_relay_setup(call))
        ws.send_json({"type": "prompt", "voicePrompt": "What is my payout status?", "last": True})
        reply = _receive_spoken_turn(ws)

    assert reply == "Your payout is scheduled for the 5th."
    db_session.refresh(call)
    assert "What is my payout status?" in call.transcript
    assert "Your payout is scheduled for the 5th." in call.transcript


def test_conversation_relay_discards_reply_after_interrupt(
    client, db_session, seeded_astrologer, monkeypatch
):
    """Does not speak a stale answer after the caller starts a new turn."""
    monkeypatch.setattr(settings, "VOICE_VALIDATE_TWILIO_SIGNATURE", False)
    call = _seed_call(db_session, seeded_astrologer)
    slow_client = _SlowFakeAgentClient([text_response("STALE reply to the first question")])
    monkeypatch.setattr("app.services.call_service.get_voice_agent_client", lambda: slow_client)

    with client.websocket_connect(
        f"/api/voice/conversation-relay?call_token={call.relay_token}"
    ) as ws:
        ws.send_json(_relay_setup(call))
        ws.send_json({"type": "prompt", "voicePrompt": "first question", "last": True})
        ws.send_json(
            {"type": "interrupt", "utteranceUntilInterrupt": "", "durationUntilInterruptMs": 100}
        )
        fast_client = FakeAgentClient([text_response("Real reply to the second question")])
        monkeypatch.setattr("app.services.call_service.get_voice_agent_client", lambda: fast_client)
        ws.send_json({"type": "prompt", "voicePrompt": "second question", "last": True})
        reply = _receive_spoken_turn(ws)

    assert reply == "Real reply to the second question"


def test_conversation_relay_websocket_rejects_unsigned_upgrade(
    client, db_session, seeded_astrologer
):
    call = _seed_call(db_session, seeded_astrologer)

    from starlette.websockets import WebSocketDisconnect

    try:
        with client.websocket_connect(
            f"/api/voice/conversation-relay?call_token={call.relay_token}"
        ):
            raised = False
    except WebSocketDisconnect:
        raised = True

    assert raised
