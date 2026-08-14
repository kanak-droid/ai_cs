from app.services import ticket_service


def test_list_my_tickets_empty(client, astrologer_auth_header):
    response = client.get("/api/tickets", headers=astrologer_auth_header)
    assert response.status_code == 200
    assert response.json() == []


def test_list_my_tickets_returns_own_tickets(client, db_session, seeded_astrologer, astrologer_auth_header):
    ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    response = client.get("/api/tickets", headers=astrologer_auth_header)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["astrologer_id"] == seeded_astrologer.id


def test_get_ticket_not_owned_by_astrologer_returns_404(
    client, db_session, seeded_astrologer, seeded_admin
):
    from app.models.astrologer import Astrologer

    other = Astrologer(
        name="Other Astrologer",
        phone="+91-90000-00001",
        language="English",
        assigned_admin_id=seeded_admin.id,
    )
    db_session.add(other)
    db_session.commit()

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=other.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    response = client.get(
        f"/api/tickets/{ticket.id}",
        headers={"Authorization": f"Bearer {seeded_astrologer.user_id}"},
    )
    assert response.status_code == 404


def test_missing_auth_header_is_rejected(client):
    response = client.get("/api/tickets")
    assert response.status_code in (401, 403)
