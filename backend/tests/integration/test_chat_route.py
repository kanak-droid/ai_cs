from app.services import chat_service
from tests.unit.test_agent_tool_selection import FakeAgentClient, FakeBlock, FakeMessage


def test_chat_route_returns_reply_and_trace(client, astrologer_auth_header, monkeypatch):
    fake_client = FakeAgentClient(
        [
            FakeMessage(
                content=[FakeBlock("tool_use", id="tool_1", name="get_payout_status", input={})],
                stop_reason="tool_use",
            ),
            FakeMessage(
                content=[FakeBlock("text", text="Your payout is scheduled.")],
                stop_reason="end_turn",
            ),
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
