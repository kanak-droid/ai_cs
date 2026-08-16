from app.integrations import queue_performance_client
from app.integrations.queue_performance_client import QueuePerformance
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


def test_chat_route_threads_history_into_the_no_visibility_gate(
    client, astrologer_auth_header, monkeypatch
):
    # End-to-end proof that `history` sent by the client actually reaches
    # SessionContext.has_prior_reply (see chat_service.handle_chat_turn) —
    # not just that the isolated tool_registry gate works in unit tests.
    def fake_get_queue_performance(db, astrologer_id):
        return QueuePerformance(
            astrologer_id=astrologer_id,
            priority=5,
            users_connected=0,
            queues_connected=0,
            total_talktime_min=0,
        )

    monkeypatch.setattr(queue_performance_client, "get_queue_performance", fake_get_queue_performance)

    fake_client = FakeAgentClient(
        [
            tool_call_response(
                "create_support_ticket",
                {
                    "category": "no_visibility",
                    "sub_category": "low_visibility",
                    "description": "Still low on calls despite trying the advice.",
                    "description_en": "Still low on calls despite trying the advice.",
                },
            ),
            text_response("Raised it for you."),
        ]
    )
    monkeypatch.setattr(chat_service, "get_agent_client", lambda: fake_client)

    response = client.post(
        "/api/chat",
        json={
            "message": "Still not getting calls after trying that",
            "history": [
                {"role": "astrologer", "text": "Why am I not getting calls?"},
                {"role": "assistant", "text": "Try staying available at peak hours..."},
            ],
        },
        headers=astrologer_auth_header,
    )

    assert response.status_code == 200
    assert response.json()["created_ticket_id"] is not None
