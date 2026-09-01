from app.core.config import settings
from app.models.enums import TicketStatus
from app.services import ticket_service

_SECRET = "test-webhook-secret"


def _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_WEBHOOK_SECRET", _SECRET)
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )
    assert ticket.zoho_ticket_id is not None  # mocked push at creation
    return ticket


def test_webhook_rejects_wrong_secret(client, db_session, seeded_astrologer, monkeypatch):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)

    response = client.post(
        "/api/integrations/zoho/webhook",
        headers={"X-Zoho-Webhook-Secret": "wrong"},
        json={"ticket_id": ticket.zoho_ticket_id, "status": "Closed"},
    )

    assert response.status_code == 403


def test_webhook_rejects_missing_secret(client, db_session, seeded_astrologer, monkeypatch):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)

    response = client.post(
        "/api/integrations/zoho/webhook",
        json={"ticket_id": ticket.zoho_ticket_id, "status": "Closed"},
    )

    assert response.status_code == 403


def test_webhook_404s_for_unknown_zoho_ticket_id(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "ZOHO_WEBHOOK_SECRET", _SECRET)

    response = client.post(
        "/api/integrations/zoho/webhook",
        headers={"X-Zoho-Webhook-Secret": _SECRET},
        json={"ticket_id": "no-such-id", "status": "Closed"},
    )

    assert response.status_code == 404


def test_webhook_closed_resolves_the_ticket_with_the_note(
    client, db_session, seeded_astrologer, monkeypatch
):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)

    response = client.post(
        "/api/integrations/zoho/webhook",
        headers={"X-Zoho-Webhook-Secret": _SECRET},
        json={"ticket_id": ticket.zoho_ticket_id, "status": "Closed", "note": "Fixed via Zoho"},
    )

    assert response.status_code == 200
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.RESOLVED
    assert ticket.history[-1].note == "Fixed via Zoho"


def test_webhook_closed_uses_a_fallback_note_when_none_given(
    client, db_session, seeded_astrologer, monkeypatch
):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)

    response = client.post(
        "/api/integrations/zoho/webhook",
        headers={"X-Zoho-Webhook-Secret": _SECRET},
        json={"ticket_id": ticket.zoho_ticket_id, "status": "Closed"},
    )

    assert response.status_code == 200
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.RESOLVED
    assert ticket.history[-1].note == "Resolved via Zoho Desk"


def test_webhook_replaying_closed_after_already_resolved_does_not_duplicate(
    client, db_session, seeded_astrologer, monkeypatch
):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)

    for _ in range(2):
        response = client.post(
            "/api/integrations/zoho/webhook",
            headers={"X-Zoho-Webhook-Secret": _SECRET},
            json={"ticket_id": ticket.zoho_ticket_id, "status": "Closed", "note": "Fixed"},
        )
        assert response.status_code == 200

    db_session.refresh(ticket)
    resolved_entries = [h for h in ticket.history if h.status == TicketStatus.RESOLVED]
    assert len(resolved_entries) == 1


def test_webhook_escalated_flags_escalated_to_kam(client, db_session, seeded_astrologer, monkeypatch):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)

    response = client.post(
        "/api/integrations/zoho/webhook",
        headers={"X-Zoho-Webhook-Secret": _SECRET},
        json={"ticket_id": ticket.zoho_ticket_id, "status": "Escalated"},
    )

    assert response.status_code == 200
    db_session.refresh(ticket)
    assert ticket.escalated_to_kam is True


def test_webhook_escalated_uses_the_kam_note_field_not_note(
    client, db_session, seeded_astrologer, monkeypatch
):
    # "note" is the "Comment to Astrologer" field — escalation must read
    # the separate "Comment to KAM" field (kam_note) instead, since an
    # escalation note is for the KAM/dashboard only, never the astrologer.
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)

    response = client.post(
        "/api/integrations/zoho/webhook",
        headers={"X-Zoho-Webhook-Secret": _SECRET},
        json={
            "ticket_id": ticket.zoho_ticket_id,
            "status": "Escalated",
            "note": "This should not be used",
            "kam_note": "Needs the KAM's personal relationship here",
        },
    )

    assert response.status_code == 200
    db_session.refresh(ticket)
    last_entry = ticket.history[-1]
    assert "Needs the KAM's personal relationship here" in last_entry.note
    assert "This should not be used" not in last_entry.note
    assert last_entry.is_status_change is False


def test_webhook_replaying_escalated_does_not_duplicate(client, db_session, seeded_astrologer, monkeypatch):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)

    for _ in range(2):
        response = client.post(
            "/api/integrations/zoho/webhook",
            headers={"X-Zoho-Webhook-Secret": _SECRET},
            json={"ticket_id": ticket.zoho_ticket_id, "status": "Escalated"},
        )
        assert response.status_code == 200

    db_session.refresh(ticket)
    escalation_entries = [h for h in ticket.history if "Escalated to KAM" in (h.note or "")]
    assert len(escalation_entries) == 1


def test_webhook_open_is_a_no_op(client, db_session, seeded_astrologer, monkeypatch):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)
    original_status = ticket.status

    response = client.post(
        "/api/integrations/zoho/webhook",
        headers={"X-Zoho-Webhook-Secret": _SECRET},
        json={"ticket_id": ticket.zoho_ticket_id, "status": "Open"},
    )

    assert response.status_code == 200
    db_session.refresh(ticket)
    assert ticket.status == original_status


def test_webhook_on_hold_transitions_to_in_progress_with_the_note(
    client, db_session, seeded_astrologer, monkeypatch
):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)

    response = client.post(
        "/api/integrations/zoho/webhook",
        headers={"X-Zoho-Webhook-Secret": _SECRET},
        json={"ticket_id": ticket.zoho_ticket_id, "status": "On Hold", "note": "Waiting on the payments team"},
    )

    assert response.status_code == 200
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.IN_PROGRESS
    assert ticket.history[-1].note == "Waiting on the payments team"


def test_webhook_on_hold_works_without_a_note(client, db_session, seeded_astrologer, monkeypatch):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)

    response = client.post(
        "/api/integrations/zoho/webhook",
        headers={"X-Zoho-Webhook-Secret": _SECRET},
        json={"ticket_id": ticket.zoho_ticket_id, "status": "On Hold"},
    )

    assert response.status_code == 200
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.IN_PROGRESS
    assert ticket.history[-1].note is None


def test_webhook_on_hold_can_fire_repeatedly_with_different_notes(
    client, db_session, seeded_astrologer, monkeypatch
):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)

    for note in ("First update", "Second update"):
        response = client.post(
            "/api/integrations/zoho/webhook",
            headers={"X-Zoho-Webhook-Secret": _SECRET},
            json={"ticket_id": ticket.zoho_ticket_id, "status": "On Hold", "note": note},
        )
        assert response.status_code == 200

    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.IN_PROGRESS
    in_progress_notes = [h.note for h in ticket.history if h.status == TicketStatus.IN_PROGRESS]
    assert in_progress_notes == ["First update", "Second update"]


def test_webhook_on_hold_does_nothing_once_a_ticket_is_terminal(
    client, db_session, seeded_astrologer, monkeypatch
):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)
    ticket_service.transition_status(
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed"
    )

    response = client.post(
        "/api/integrations/zoho/webhook",
        headers={"X-Zoho-Webhook-Secret": _SECRET},
        json={"ticket_id": ticket.zoho_ticket_id, "status": "On Hold", "note": "too late"},
    )

    assert response.status_code == 200
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.RESOLVED
