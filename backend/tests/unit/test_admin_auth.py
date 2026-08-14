from app.models.admin import Admin
from app.models.enums import AdminAccessLevel, AdminRole
from app.services import auth_service


def test_grant_access_has_no_domain_restriction(db_session):
    # Any email works now — CS admins on dostt.in/sahijobs.com email domains
    # are a real case, not just a hypothetical.
    admin = auth_service.grant_access(
        db_session,
        email="someone@dostt.in",
        name="Someone",
        role=AdminRole.CS,
        access_level=AdminAccessLevel.NORMAL,
    )
    assert admin.email == "someone@dostt.in"
    assert auth_service.login_admin(db_session, "someone@dostt.in", "astroHelp@123") is not None


def test_grant_access_creates_a_normal_admin_with_the_normal_password(db_session):
    admin = auth_service.grant_access(
        db_session,
        email="new.kam@getlokalapp.com",
        name="New KAM",
        role=AdminRole.KAM,
        access_level=AdminAccessLevel.NORMAL,
    )

    assert admin.role == AdminRole.KAM
    assert admin.access_level == AdminAccessLevel.NORMAL
    assert admin.is_active is True

    result = auth_service.login_admin(db_session, "new.kam@getlokalapp.com", "astroHelp@123")
    assert result is not None
    assert result[0].id == admin.id


def test_grant_access_creates_an_admin_access_admin_with_the_admin_password(db_session):
    admin = auth_service.grant_access(
        db_session,
        email="new.super@getlokalapp.com",
        name="New Super",
        role=AdminRole.CS,
        access_level=AdminAccessLevel.ADMIN,
    )

    assert admin.access_level == AdminAccessLevel.ADMIN

    # The normal-tier password does not work for an admin-access account...
    assert auth_service.login_admin(db_session, "new.super@getlokalapp.com", "astroHelp@123") is None
    # ...only the admin-tier password does.
    result = auth_service.login_admin(db_session, "new.super@getlokalapp.com", "astroHelpAdmin@123")
    assert result is not None
    assert result[0].id == admin.id


def test_granting_access_again_updates_role_and_resets_password_to_the_new_tier(db_session):
    auth_service.grant_access(
        db_session,
        email="promote-me@getlokalapp.com",
        name="Promote Me",
        role=AdminRole.KAM,
        access_level=AdminAccessLevel.NORMAL,
    )
    assert auth_service.login_admin(db_session, "promote-me@getlokalapp.com", "astroHelp@123") is not None

    auth_service.grant_access(
        db_session,
        email="promote-me@getlokalapp.com",
        name="Promote Me",
        role=AdminRole.KAM,
        access_level=AdminAccessLevel.ADMIN,
    )

    # Old (normal-tier) password no longer works once promoted...
    assert auth_service.login_admin(db_session, "promote-me@getlokalapp.com", "astroHelp@123") is None
    # ...the new admin-tier password does.
    assert (
        auth_service.login_admin(db_session, "promote-me@getlokalapp.com", "astroHelpAdmin@123")
        is not None
    )


def test_login_rejects_an_admin_with_no_password_set(db_session):
    admin = Admin(name="No Password Yet", email="no-password@getlokalapp.com", password_hash=None)
    db_session.add(admin)
    db_session.commit()

    result = auth_service.login_admin(db_session, "no-password@getlokalapp.com", "anything")

    assert result is None


def test_login_rejects_a_deactivated_admin(db_session):
    auth_service.grant_access(
        db_session,
        email="deactivated@getlokalapp.com",
        name="Deactivated",
        role=AdminRole.KAM,
        access_level=AdminAccessLevel.NORMAL,
    )
    admin = db_session.query(Admin).filter_by(email="deactivated@getlokalapp.com").one()
    admin.is_active = False
    db_session.commit()

    result = auth_service.login_admin(db_session, "deactivated@getlokalapp.com", "astroHelp@123")

    assert result is None
