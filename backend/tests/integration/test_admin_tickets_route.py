from app.integrations import object_storage
from app.models.admin import Admin
from app.models.enums import AdminRole
from app.services import ticket_service


def test_get_attachment_returns_a_signed_preview_url_not_the_raw_one(
    client, db_session, seeded_astrologer, admin_auth_header, monkeypatch
):
    # The browser has no AWS credentials, so this route hands back a
    # short-lived signed URL (via object_storage, our own credentials)
    # rather than the ticket's raw S3 URL — that URL 403s on a plain
    # unauthenticated GET unless the bucket has a public-read policy
    # attached (confirmed live 2026-08-18); the signed one works regardless
    # and the browser can load it directly.
    raw_url = "https://dev-astro.s3.ap-south-1.amazonaws.com/supply-issues/photo.jpg"
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="technical",
        sub_category="app_crash",
        description="crash",
        description_en="crash",
        preferred_language="English",
        attachment_url=raw_url,
    )

    monkeypatch.setattr(
        object_storage, "generate_preview_url", lambda url: f"{url}?signed=1"
    )

    response = client.get(f"/api/admin/tickets/{ticket.id}/attachment", headers=admin_auth_header)

    assert response.status_code == 200
    assert response.json() == {"preview_url": f"{raw_url}?signed=1"}


def test_get_attachment_404s_when_the_ticket_has_none(
    client, db_session, seeded_astrologer, admin_auth_header
):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="no photo",
        description_en="no photo",
        preferred_language="English",
    )

    response = client.get(f"/api/admin/tickets/{ticket.id}/attachment", headers=admin_auth_header)

    assert response.status_code == 404


def test_get_attachment_requires_admin_auth(client, db_session, seeded_astrologer):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    response = client.get(f"/api/admin/tickets/{ticket.id}/attachment")

    assert response.status_code in (401, 403)


def test_reassign_route_moves_ownership_and_logs_history(
    client, db_session, seeded_astrologer, admin_access_auth_header
):
    other_kam = Admin(name="Other KAM", email="otherkam@test.example", role=AdminRole.KAM)
    db_session.add(other_kam)
    db_session.commit()
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    response = client.post(
        f"/api/admin/tickets/{ticket.id}/reassign",
        headers=admin_access_auth_header,
        json={"role": "kam", "admin_id": other_kam.id, "note": "Covering leave"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assigned_admin_id"] == other_kam.id
    assert body["kam_notified"] is True
    assert "Covering leave" in body["history"][-1]["note"]


def test_reassign_route_requires_admin_access(client, db_session, seeded_astrologer, admin_auth_header):
    # Normal-access KAM/CS accounts can't reassign ownership — same
    # ADMIN-access-level bar as granting/editing another admin's access.
    other_kam = Admin(name="Other KAM 2", email="otherkam2@test.example", role=AdminRole.KAM)
    db_session.add(other_kam)
    db_session.commit()
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    response = client.post(
        f"/api/admin/tickets/{ticket.id}/reassign",
        headers=admin_auth_header,
        json={"role": "kam", "admin_id": other_kam.id},
    )

    assert response.status_code == 403


def test_reassign_route_rejects_an_admin_on_leave(
    client, db_session, seeded_astrologer, admin_access_auth_header
):
    on_leave_kam = Admin(
        name="On Leave KAM",
        email="onleave@test.example",
        role=AdminRole.KAM,
        is_temporarily_inactive=True,
    )
    db_session.add(on_leave_kam)
    db_session.commit()
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    response = client.post(
        f"/api/admin/tickets/{ticket.id}/reassign",
        headers=admin_access_auth_header,
        json={"role": "kam", "admin_id": on_leave_kam.id},
    )

    assert response.status_code == 400


def test_escalate_route_flags_the_ticket(client, db_session, seeded_astrologer, admin_auth_header):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    response = client.post(
        f"/api/admin/tickets/{ticket.id}/escalate",
        headers=admin_auth_header,
        json={"note": "Needs KAM's attention"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["escalated_to_kam"] is True
    assert body["kam_notified"] is True


def test_escalate_route_rejects_a_blank_comment(client, db_session, seeded_astrologer, admin_auth_header):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    response = client.post(
        f"/api/admin/tickets/{ticket.id}/escalate",
        headers=admin_auth_header,
        json={"note": ""},
    )

    assert response.status_code == 400


def test_update_status_route_rejects_closed(client, db_session, seeded_astrologer, admin_auth_header):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    response = client.patch(
        f"/api/admin/tickets/{ticket.id}",
        headers=admin_auth_header,
        json={"status": "closed", "note": "trying to close directly"},
    )

    assert response.status_code == 400


def test_update_status_route_rejects_resolve_with_no_comment(
    client, db_session, seeded_astrologer, admin_auth_header
):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    response = client.patch(
        f"/api/admin/tickets/{ticket.id}",
        headers=admin_auth_header,
        json={"status": "resolved"},
    )

    assert response.status_code == 400


def test_update_status_route_accepts_resolve_with_a_comment(
    client, db_session, seeded_astrologer, admin_auth_header
):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    response = client.patch(
        f"/api/admin/tickets/{ticket.id}",
        headers=admin_auth_header,
        json={"status": "resolved", "note": "Fixed the login issue"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


def _make_ticket(db_session, seeded_astrologer):
    return ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )


def test_bulk_reassign_route_moves_ownership_of_every_ticket(
    client, db_session, seeded_astrologer, admin_access_auth_header
):
    other_kam = Admin(name="Bulk Target KAM", email="bulktarget@test.example", role=AdminRole.KAM)
    db_session.add(other_kam)
    db_session.commit()
    tickets = [_make_ticket(db_session, seeded_astrologer) for _ in range(3)]

    response = client.post(
        "/api/admin/tickets/bulk-reassign",
        headers=admin_access_auth_header,
        json={
            "ticket_ids": [t.id for t in tickets],
            "role": "kam",
            "admin_id": other_kam.id,
            "note": "Covering for a departing KAM",
        },
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert all(r["ok"] for r in results)
    assert {r["ticket_id"] for r in results} == {t.id for t in tickets}
    for t in tickets:
        db_session.refresh(t)
        assert t.assigned_admin_id == other_kam.id


def test_bulk_reassign_route_requires_admin_access(
    client, db_session, seeded_astrologer, admin_auth_header
):
    other_kam = Admin(name="Bulk Target KAM 2", email="bulktarget2@test.example", role=AdminRole.KAM)
    db_session.add(other_kam)
    db_session.commit()
    ticket = _make_ticket(db_session, seeded_astrologer)

    response = client.post(
        "/api/admin/tickets/bulk-reassign",
        headers=admin_auth_header,
        json={"ticket_ids": [ticket.id], "role": "kam", "admin_id": other_kam.id},
    )

    assert response.status_code == 403


def test_bulk_reassign_route_reports_a_failure_per_ticket_without_failing_the_whole_batch(
    client, db_session, seeded_astrologer, admin_access_auth_header
):
    other_kam = Admin(name="Bulk Target KAM 3", email="bulktarget3@test.example", role=AdminRole.KAM)
    db_session.add(other_kam)
    db_session.commit()
    good_ticket = _make_ticket(db_session, seeded_astrologer)
    missing_ticket_id = good_ticket.id + 999999

    response = client.post(
        "/api/admin/tickets/bulk-reassign",
        headers=admin_access_auth_header,
        json={
            "ticket_ids": [good_ticket.id, missing_ticket_id],
            "role": "kam",
            "admin_id": other_kam.id,
        },
    )

    assert response.status_code == 200
    results = {r["ticket_id"]: r for r in response.json()["results"]}
    assert results[good_ticket.id]["ok"] is True
    assert results[missing_ticket_id]["ok"] is False
    assert results[missing_ticket_id]["error"] is not None
    db_session.refresh(good_ticket)
    assert good_ticket.assigned_admin_id == other_kam.id


def test_bulk_reassign_route_rejects_an_admin_on_leave(
    client, db_session, seeded_astrologer, admin_access_auth_header
):
    on_leave_kam = Admin(
        name="Bulk On Leave KAM",
        email="bulkonleave@test.example",
        role=AdminRole.KAM,
        is_temporarily_inactive=True,
    )
    db_session.add(on_leave_kam)
    db_session.commit()
    ticket = _make_ticket(db_session, seeded_astrologer)

    response = client.post(
        "/api/admin/tickets/bulk-reassign",
        headers=admin_access_auth_header,
        json={"ticket_ids": [ticket.id], "role": "kam", "admin_id": on_leave_kam.id},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["ok"] is False
