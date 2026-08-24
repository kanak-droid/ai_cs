from app.integrations import zoho_client
from app.models.admin import Admin
from app.models.enums import AdminRole, TicketStatus
from app.services import chat_session_service, ticket_service


def test_create_ticket_pushes_cs_notified_tickets_to_zoho(db_session, seeded_astrologer):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    assert ticket.cs_notified is True
    assert ticket.zoho_ticket_id is not None


def test_create_ticket_uploads_the_attachment_when_present(db_session, seeded_astrologer, monkeypatch):
    calls = []
    monkeypatch.setattr(
        zoho_client, "upload_attachment", lambda zoho_id, url: calls.append((zoho_id, url))
    )

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
        attachment_url="http://localhost:8000/uploads/photo.jpg",
    )

    assert calls == [(ticket.zoho_ticket_id, "http://localhost:8000/uploads/photo.jpg")]


def test_create_ticket_does_not_upload_when_no_attachment(db_session, seeded_astrologer, monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("upload_attachment should never be called with no attachment_url")

    monkeypatch.setattr(zoho_client, "upload_attachment", _boom)

    ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )


def test_a_zoho_attachment_upload_failure_never_blocks_ticket_creation(
    db_session, seeded_astrologer, monkeypatch
):
    def _boom(*args, **kwargs):
        raise RuntimeError("Zoho is down")

    monkeypatch.setattr(zoho_client, "upload_attachment", _boom)

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
        attachment_url="http://localhost:8000/uploads/photo.jpg",
    )

    assert ticket.id is not None
    assert ticket.zoho_ticket_id is not None


def test_create_ticket_does_not_push_profile_category_tickets(db_session, seeded_astrologer):
    # "profile" (photo change) never loops in a CS at all — see
    # _ALWAYS_DIRECT_TO_KAM_CATEGORIES — so it should never reach Zoho either.
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="profile",
        sub_category="photo_change",
        description="new photo",
        description_en="new photo",
        preferred_language="English",
    )

    assert ticket.cs_notified is False
    assert ticket.zoho_ticket_id is None


def test_reassigning_to_a_cs_pushes_a_not_yet_pushed_ticket(db_session, seeded_astrologer):
    cs_admin = Admin(name="Test CS", email="cs-zoho@test.example", role=AdminRole.CS)
    db_session.add(cs_admin)
    db_session.commit()

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="profile",
        sub_category="photo_change",
        description="new photo",
        description_en="new photo",
        preferred_language="English",
    )
    assert ticket.zoho_ticket_id is None

    ticket = ticket_service.reassign_ticket(
        db_session, ticket, role="cs", new_admin_id=cs_admin.id, changed_by="admin@test.example"
    )

    assert ticket.cs_notified is True
    assert ticket.zoho_ticket_id is not None


def test_a_zoho_failure_never_blocks_ticket_creation(db_session, seeded_astrologer, monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("Zoho is down")

    monkeypatch.setattr(zoho_client, "create_ticket", _boom)

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    assert ticket.id is not None
    assert ticket.zoho_ticket_id is None


def test_a_zoho_failure_never_blocks_a_status_transition(db_session, seeded_astrologer, monkeypatch):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )
    assert ticket.zoho_ticket_id is not None  # mocked push succeeded at creation

    def _boom(*args, **kwargs):
        raise RuntimeError("Zoho is down")

    monkeypatch.setattr(zoho_client, "update_status", _boom)

    ticket = ticket_service.transition_status(
        db_session, ticket, TicketStatus.IN_PROGRESS, changed_by="admin@test.example"
    )

    assert ticket.status == TicketStatus.IN_PROGRESS


def test_escalating_pushes_escalated_status_to_zoho(db_session, seeded_astrologer, monkeypatch):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )
    assert ticket.zoho_ticket_id is not None

    calls = []
    monkeypatch.setattr(
        zoho_client, "update_status", lambda zoho_id, status: calls.append((zoho_id, status))
    )

    ticket = ticket_service.escalate_to_kam(
        db_session, ticket, changed_by="cs@test.example", note="Needs KAM's attention"
    )

    assert ticket.escalated_to_kam is True
    assert calls == [(ticket.zoho_ticket_id, "Escalated")]


def test_reassigning_an_already_pushed_ticket_updates_the_zoho_assignee(
    db_session, seeded_astrologer, monkeypatch
):
    original_cs = Admin(name="Original CS", email="original-cs@test.example", role=AdminRole.CS)
    new_cs = Admin(name="New CS", email="new-cs@test.example", role=AdminRole.CS)
    db_session.add_all([original_cs, new_cs])
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
    assert ticket.zoho_ticket_id is not None  # already pushed at creation

    monkeypatch.setattr(zoho_client, "find_agent_id_by_email", lambda email: f"zoho-agent-for-{email}")
    calls = []
    monkeypatch.setattr(
        zoho_client, "update_assignee", lambda zoho_id, agent_id: calls.append((zoho_id, agent_id))
    )

    ticket = ticket_service.reassign_ticket(
        db_session, ticket, role="cs", new_admin_id=new_cs.id, changed_by="admin@test.example"
    )

    assert calls == [(ticket.zoho_ticket_id, f"zoho-agent-for-{new_cs.email}")]


def test_reassigning_with_no_matching_agent_does_not_call_update_assignee(
    db_session, seeded_astrologer, monkeypatch
):
    new_cs = Admin(name="New CS", email="new-cs-2@test.example", role=AdminRole.CS)
    db_session.add(new_cs)
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

    monkeypatch.setattr(zoho_client, "find_agent_id_by_email", lambda email: None)

    def _boom(*args, **kwargs):
        raise AssertionError("update_assignee should never be called with no matching agent")

    monkeypatch.setattr(zoho_client, "update_assignee", _boom)

    ticket_service.reassign_ticket(
        db_session, ticket, role="cs", new_admin_id=new_cs.id, changed_by="admin@test.example"
    )


def test_a_zoho_assignee_update_failure_never_blocks_reassignment(
    db_session, seeded_astrologer, monkeypatch
):
    new_cs = Admin(name="New CS", email="new-cs-3@test.example", role=AdminRole.CS)
    db_session.add(new_cs)
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

    monkeypatch.setattr(zoho_client, "find_agent_id_by_email", lambda email: "some-agent-id")

    def _boom(*args, **kwargs):
        raise RuntimeError("Zoho is down")

    monkeypatch.setattr(zoho_client, "update_assignee", _boom)

    ticket = ticket_service.reassign_ticket(
        db_session, ticket, role="cs", new_admin_id=new_cs.id, changed_by="admin@test.example"
    )

    assert ticket.assigned_cs_id == new_cs.id


def test_sync_chat_transcript_posts_the_full_conversation(db_session, seeded_astrologer, monkeypatch):
    session = chat_session_service.get_or_create_session(db_session, "sess-zoho-1", seeded_astrologer.id)
    chat_session_service.record_message(db_session, session, role="astrologer", text="My payout is late")
    chat_session_service.record_message(db_session, session, role="assistant", text="Let me check")

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    calls = []
    monkeypatch.setattr(
        zoho_client, "post_comment", lambda zoho_id, comment: calls.append((zoho_id, comment))
    )

    ticket_service.sync_chat_transcript_to_zoho(db_session, ticket, "sess-zoho-1")

    assert calls == [
        (ticket.zoho_ticket_id, "Astrologer: My payout is late\n\nAssistant: Let me check")
    ]


def test_sync_chat_transcript_does_nothing_when_ticket_was_never_pushed(
    db_session, seeded_astrologer, monkeypatch
):
    session = chat_session_service.get_or_create_session(db_session, "sess-zoho-2", seeded_astrologer.id)
    chat_session_service.record_message(db_session, session, role="astrologer", text="Photo change")

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="profile",
        sub_category="photo_change",
        description="new photo",
        description_en="new photo",
        preferred_language="English",
    )
    assert ticket.zoho_ticket_id is None

    def _boom(*args, **kwargs):
        raise AssertionError("post_comment should never be called for a ticket never pushed to Zoho")

    monkeypatch.setattr(zoho_client, "post_comment", _boom)

    ticket_service.sync_chat_transcript_to_zoho(db_session, ticket, "sess-zoho-2")


def test_sync_chat_transcript_does_nothing_without_a_transcript(db_session, seeded_astrologer, monkeypatch):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    def _boom(*args, **kwargs):
        raise AssertionError("post_comment should never be called with no transcript")

    monkeypatch.setattr(zoho_client, "post_comment", _boom)

    # No session_id at all — e.g. a direct executor call in tests.
    ticket_service.sync_chat_transcript_to_zoho(db_session, ticket, None)


def test_a_zoho_transcript_post_failure_never_raises(db_session, seeded_astrologer, monkeypatch):
    session = chat_session_service.get_or_create_session(db_session, "sess-zoho-3", seeded_astrologer.id)
    chat_session_service.record_message(db_session, session, role="astrologer", text="Help")

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    def _boom(*args, **kwargs):
        raise RuntimeError("Zoho is down")

    monkeypatch.setattr(zoho_client, "post_comment", _boom)

    # Must not raise.
    ticket_service.sync_chat_transcript_to_zoho(db_session, ticket, "sess-zoho-3")
