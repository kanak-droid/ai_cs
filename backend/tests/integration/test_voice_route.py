from app.core.config import settings
from app.models.call import Call
from app.models.enums import CallStatus
from tests.unit.test_agent_tool_selection import FakeAgentClient, text_response

_SECRET = "test-vapi-secret"


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
    assert call.vapi_call_id is not None  # mocked, but always set
    assert call.status == CallStatus.QUEUED


def _seed_call(db_session, seeded_astrologer, vapi_call_id="vapi-call-abc"):
    call = Call(
        astrologer_id=seeded_astrologer.id,
        phone_number=seeded_astrologer.phone,
        vapi_call_id=vapi_call_id,
        status=CallStatus.IN_PROGRESS,
    )
    db_session.add(call)
    db_session.commit()
    return call


def test_custom_llm_rejects_wrong_secret(client, db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "VAPI_WEBHOOK_SECRET", _SECRET)
    call = _seed_call(db_session, seeded_astrologer)

    response = client.post(
        "/api/voice/custom-llm",
        headers={"x-vapi-secret": "wrong"},
        json={"messages": [{"role": "user", "content": "hi"}], "call": {"id": call.vapi_call_id}},
    )

    assert response.status_code == 403


def test_custom_llm_runs_the_same_orchestrator_as_chat(
    client, db_session, seeded_astrologer, monkeypatch
):
    monkeypatch.setattr(settings, "VAPI_WEBHOOK_SECRET", _SECRET)
    call = _seed_call(db_session, seeded_astrologer)

    fake_client = FakeAgentClient([text_response("Your payout is scheduled for the 5th.")])
    monkeypatch.setattr("app.services.call_service.get_voice_agent_client", lambda: fake_client)

    response = client.post(
        "/api/voice/custom-llm",
        headers={"x-vapi-secret": _SECRET},
        json={
            "messages": [
                {"role": "system", "content": "You are on a phone call."},
                {"role": "user", "content": "What is my payout status?"},
            ],
            "call": {"id": call.vapi_call_id},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "Your payout is scheduled for the 5th."

    db_session.refresh(call)
    assert "What is my payout status?" in call.transcript
    assert "Your payout is scheduled for the 5th." in call.transcript


def test_custom_llm_unknown_call_id_gets_a_spoken_fallback_not_a_500(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "VAPI_WEBHOOK_SECRET", _SECRET)

    response = client.post(
        "/api/voice/custom-llm",
        headers={"x-vapi-secret": _SECRET},
        json={"messages": [{"role": "user", "content": "hi"}], "call": {}},
    )

    assert response.status_code == 200
    assert "trouble" in response.json()["choices"][0]["message"]["content"].lower()


def test_events_webhook_marks_call_ended_on_end_of_call_report(
    client, db_session, seeded_astrologer, monkeypatch
):
    monkeypatch.setattr(settings, "VAPI_WEBHOOK_SECRET", _SECRET)
    call = _seed_call(db_session, seeded_astrologer)

    response = client.post(
        "/api/voice/events",
        headers={"x-vapi-secret": _SECRET},
        json={
            "message": {
                "type": "end-of-call-report",
                "endedReason": "customer-ended-call",
                "call": {"id": call.vapi_call_id},
                "artifact": {"transcript": "Astrologer: hi\nAgent: bye"},
            }
        },
    )

    assert response.status_code == 200
    db_session.refresh(call)
    assert call.status == CallStatus.ENDED
    assert call.ended_reason == "customer-ended-call"
    assert call.ended_at is not None
    assert call.transcript == "Astrologer: hi\nAgent: bye"


def test_events_webhook_rejects_missing_secret(client, db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "VAPI_WEBHOOK_SECRET", _SECRET)
    call = _seed_call(db_session, seeded_astrologer)

    response = client.post(
        "/api/voice/events",
        json={"message": {"type": "end-of-call-report", "call": {"id": call.vapi_call_id}}},
    )

    assert response.status_code == 403
