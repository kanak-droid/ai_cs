from app.integrations import queue_performance_client
from app.integrations.queue_performance_client import QueuePerformance
from app.models.astrologer import Astrologer
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.enums import SessionResolution


def _fake_priority(priority_by_astrologer: dict[int, int | None]):
    def _fake(db, astrologer_id):
        return QueuePerformance(
            astrologer_id=astrologer_id,
            priority=priority_by_astrologer.get(astrologer_id),
            users_connected=0,
            queues_connected=0,
            total_talktime_min=0,
        )

    return _fake


def test_list_chat_sessions_sorts_by_priority(
    client, db_session, seeded_admin, admin_auth_header, monkeypatch
):
    p1_astrologer = Astrologer(
        name="P1 Astrologer", phone="+91-1", language="English", assigned_admin_id=seeded_admin.id
    )
    p4_astrologer = Astrologer(
        name="P4 Astrologer", phone="+91-2", language="English", assigned_admin_id=seeded_admin.id
    )
    db_session.add_all([p1_astrologer, p4_astrologer])
    db_session.commit()

    db_session.add(ChatSession(session_id="sess-p4", astrologer_id=p4_astrologer.id))
    db_session.add(ChatSession(session_id="sess-p1", astrologer_id=p1_astrologer.id))
    db_session.commit()

    monkeypatch.setattr(
        queue_performance_client,
        "get_queue_performance",
        _fake_priority({p1_astrologer.id: 1, p4_astrologer.id: 4}),
    )

    response = client.get("/api/admin/chat-sessions", headers=admin_auth_header)

    assert response.status_code == 200
    body = response.json()
    session_ids = [row["session_id"] for row in body]
    assert session_ids.index("sess-p1") < session_ids.index("sess-p4")
    p1_row = next(row for row in body if row["session_id"] == "sess-p1")
    assert p1_row["astrologer_name"] == "P1 Astrologer"
    assert p1_row["priority"] == 1


def test_get_chat_session_returns_the_full_transcript_in_order(
    client, db_session, seeded_astrologer, admin_auth_header
):
    session = ChatSession(
        session_id="sess-detail-1",
        astrologer_id=seeded_astrologer.id,
        resolved_by=SessionResolution.BOT,
    )
    db_session.add(session)
    db_session.commit()
    db_session.add(ChatMessage(session_id=session.id, role="astrologer", text="Why is my payout low?"))
    db_session.add(ChatMessage(session_id=session.id, role="assistant", text="Let me check that."))
    db_session.commit()

    response = client.get(f"/api/admin/chat-sessions/{session.id}", headers=admin_auth_header)

    assert response.status_code == 200
    body = response.json()
    assert body["resolved_by"] == "bot"
    assert [(m["role"], m["text"]) for m in body["messages"]] == [
        ("astrologer", "Why is my payout low?"),
        ("assistant", "Let me check that."),
    ]


def test_get_chat_session_404s_for_an_unknown_id(client, admin_auth_header):
    response = client.get("/api/admin/chat-sessions/999999", headers=admin_auth_header)

    assert response.status_code == 404


def test_chat_sessions_route_requires_admin_auth(client):
    response = client.get("/api/admin/chat-sessions")

    assert response.status_code in (401, 403)
