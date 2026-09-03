from app.core.config import settings
from app.models.call import Call
from app.services import ticket_service


def _create_ticket(db_session, seeded_astrologer):
    """Creates the support ticket used by the ticket-call endpoint tests."""
    return ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="payout",
        sub_category="delayed_payout",
        description="Payout is delayed",
        description_en="Payout is delayed",
        preferred_language="English",
    )


def test_admin_can_start_and_list_a_ticket_followup_call(
    client, db_session, seeded_astrologer, admin_access_auth_header
):
    ticket = _create_ticket(db_session, seeded_astrologer)

    response = client.post(
        f"/api/admin/tickets/{ticket.id}/follow-up-calls",
        headers=admin_access_auth_header,
        json={"reason": "demo", "recipient_phone": "+18312490630"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == ticket.id
    assert body["phone_number"] == "+18312490630"
    assert body["triggered_by"].endswith(":demo")

    response = client.get(
        f"/api/admin/tickets/{ticket.id}/follow-up-calls", headers=admin_access_auth_header
    )
    assert response.status_code == 200
    assert [call["id"] for call in response.json()] == [body["id"]]


def test_astrologer_can_view_calls_for_their_own_ticket(
    client, db_session, seeded_astrologer, astrologer_auth_header
):
    ticket = _create_ticket(db_session, seeded_astrologer)
    call = Call(
        astrologer_id=seeded_astrologer.id,
        ticket_id=ticket.id,
        phone_number=seeded_astrologer.phone,
        triggered_by="ticket_created",
        relay_token="token-for-ticket-call",
    )
    db_session.add(call)
    db_session.commit()

    response = client.get(
        f"/api/tickets/{ticket.id}/follow-up-calls", headers=astrologer_auth_header
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == call.id


def test_ticket_creation_can_schedule_a_followup_call_when_enabled(
    db_session, seeded_astrologer, monkeypatch
):
    monkeypatch.setattr(settings, "VOICE_AUTO_CALL_ON_TICKET_CREATE", True)

    ticket = _create_ticket(db_session, seeded_astrologer)

    call = db_session.query(Call).filter_by(ticket_id=ticket.id).one()
    assert call.triggered_by == "ticket_created"
    assert call.twilio_call_sid is not None


def test_admin_voice_call_queue_exposes_completed_support_outcome(
    client, db_session, seeded_astrologer, admin_auth_header
):
    call = Call(
        astrologer_id=seeded_astrologer.id,
        phone_number=seeded_astrologer.phone,
        triggered_by="user_request",
        relay_token="queue-call-token",
        support_summary="The payout date was explained.",
        resolution_status="resolved",
        suggested_solution="Wait for the scheduled payout.",
        next_action="No further action required.",
        actions_taken=[{"tool": "get_payout_status", "ok": True, "summary": "Payout found"}],
    )
    db_session.add(call)
    db_session.commit()

    response = client.get("/api/admin/voice-calls", headers=admin_auth_header)

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == call.id
    assert body[0]["support_summary"] == "The payout date was explained."
    assert body[0]["resolution_status"] == "resolved"
