def test_normal_admin_cannot_create_an_admin(client, admin_auth_header):
    response = client.post(
        "/api/admin/admins",
        headers=admin_auth_header,
        json={"name": "New Person", "email": "new.person@getlokalapp.com", "role": "kam"},
    )
    assert response.status_code == 403


def test_admin_access_admin_can_create_an_admin(client, admin_access_auth_header):
    response = client.post(
        "/api/admin/admins",
        headers=admin_access_auth_header,
        json={
            "name": "New Person",
            "email": "new.person@getlokalapp.com",
            "role": "kam",
            "access_level": "admin",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new.person@getlokalapp.com"
    assert body["access_level"] == "admin"


def test_normal_admin_cannot_edit_another_admins_access(client, admin_auth_header, seeded_admin):
    response = client.patch(
        f"/api/admin/admins/{seeded_admin.id}",
        headers=admin_auth_header,
        json={"access_level": "admin"},
    )
    assert response.status_code == 403


def test_admin_access_admin_can_promote_another_admin(client, admin_access_auth_header, seeded_admin):
    response = client.patch(
        f"/api/admin/admins/{seeded_admin.id}",
        headers=admin_access_auth_header,
        json={"access_level": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["access_level"] == "admin"


def test_normal_admin_cannot_list_the_full_roster(client, admin_auth_header):
    response = client.get("/api/admin/admins?include_inactive=true", headers=admin_auth_header)
    assert response.status_code == 403


def test_normal_admin_can_still_list_active_admins_for_the_ticket_filter(client, admin_auth_header):
    response = client.get("/api/admin/admins", headers=admin_auth_header)
    assert response.status_code == 200


def test_admin_access_admin_can_list_the_full_roster(client, admin_access_auth_header):
    response = client.get("/api/admin/admins?include_inactive=true", headers=admin_access_auth_header)
    assert response.status_code == 200


def test_admin_access_admin_can_mark_another_admin_on_leave(
    client, admin_access_auth_header, seeded_admin
):
    response = client.patch(
        f"/api/admin/admins/{seeded_admin.id}",
        headers=admin_access_auth_header,
        json={"is_temporarily_inactive": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_temporarily_inactive"] is True
    # Unlike permanent deactivation, on leave keeps is_active true.
    assert body["is_active"] is True


def test_an_admin_on_leave_still_appears_in_the_default_active_list(
    client, admin_auth_header, admin_access_auth_header, seeded_admin
):
    client.patch(
        f"/api/admin/admins/{seeded_admin.id}",
        headers=admin_access_auth_header,
        json={"is_temporarily_inactive": True},
    )

    response = client.get("/api/admin/admins", headers=admin_auth_header)
    assert response.status_code == 200
    ids = [a["id"] for a in response.json()]
    assert seeded_admin.id in ids
