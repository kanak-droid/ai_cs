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


def test_webhook_open_and_on_hold_are_no_ops(client, db_session, seeded_astrologer, monkeypatch):
    ticket = _make_pushed_ticket(db_session, seeded_astrologer, monkeypatch)
    original_status = ticket.status

    for zoho_status in ("Open", "On Hold"):
        response = client.post(
            "/api/integrations/zoho/webhook",
            headers={"X-Zoho-Webhook-Secret": _SECRET},
            json={"ticket_id": ticket.zoho_ticket_id, "status": zoho_status},
        )
        assert response.status_code == 200

    db_session.refresh(ticket)
    assert ticket.status == original_status
