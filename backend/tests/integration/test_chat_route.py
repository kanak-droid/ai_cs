from app.services import chat_service
from tests.unit.test_agent_tool_selection import FakeAgentClient, text_response, tool_call_response


def test_chat_route_returns_reply_and_trace(client, astrologer_auth_header, monkeypatch):
    fake_client = FakeAgentClient(
        [
            tool_call_response("get_payout_status"),
            text_response("Your payout is scheduled."),
        ]
    )
    monkeypatch.setattr(chat_service, "get_agent_client", lambda: fake_client)

    response = client.post(
        "/api/chat", json={"message": "When is my payout?"}, headers=astrologer_auth_header
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Your payout is scheduled."
    assert body["trace"] == [
        {"tool": "get_payout_status", "ok": True, "summary": "Checked your payout status"}
    ]


def test_chat_route_requires_auth(client):
    response = client.post("/api/chat", json={"message": "hi"})
    assert response.status_code in (401, 403)
