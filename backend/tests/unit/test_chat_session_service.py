from app.models.chat_session import ChatSession
from app.models.enums import SessionResolution
from app.services import chat_session_service, ticket_service


def test_get_or_create_session_is_idempotent(db_session, seeded_astrologer):
    first = chat_session_service.get_or_create_session(db_session, "sess-1", seeded_astrologer.id)
    second = chat_session_service.get_or_create_session(db_session, "sess-1", seeded_astrologer.id)

    assert first.id == second.id
    assert db_session.query(ChatSession).filter_by(session_id="sess-1").count() == 1


def test_get_or_create_session_without_id_is_a_noop(db_session, seeded_astrologer):
    assert chat_session_service.get_or_create_session(db_session, None, seeded_astrologer.id) is None


def test_mark_resolved_by_bot_sets_category_and_resolution(db_session, seeded_astrologer):
    chat_session_service.get_or_create_session(db_session, "sess-2", seeded_astrologer.id)

    chat_session_service.mark_resolved_by_bot(
        db_session, "sess-2", category="payout", sub_category="payout_delay"
    )

    session = db_session.query(ChatSession).filter_by(session_id="sess-2").one()
    assert session.resolved_by == SessionResolution.BOT
    assert session.category == "payout"
    assert session.resolved_at is not None


def test_mark_escalated_links_the_ticket(db_session, seeded_astrologer):
    chat_session_service.get_or_create_session(db_session, "sess-3", seeded_astrologer.id)
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="technical",
        sub_category="app_crash",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    chat_session_service.mark_escalated(db_session, "sess-3", ticket_id=ticket.id)

    session = db_session.query(ChatSession).filter_by(session_id="sess-3").one()
    assert session.resolved_by == SessionResolution.ESCALATED
    assert session.ticket_id == ticket.id


def test_record_feedback_stores_rating_and_comment_for_the_owning_astrologer(
    db_session, seeded_astrologer
):
    chat_session_service.get_or_create_session(db_session, "sess-4", seeded_astrologer.id)

    session = chat_session_service.record_feedback(
        db_session,
        "sess-4",
        seeded_astrologer.id,
        rating=5,
        reasons=["Quick response"],
        comment="Fixed it fast!",
    )

    assert session is not None
    assert session.rating == 5
    assert session.feedback_reasons == ["Quick response"]
    assert session.feedback_text == "Fixed it fast!"


def test_record_feedback_rejects_a_different_astrologers_session(db_session, seeded_astrologer):
    chat_session_service.get_or_create_session(db_session, "sess-5", seeded_astrologer.id)

    result = chat_session_service.record_feedback(
        db_session, "sess-5", seeded_astrologer.id + 999, rating=1, comment=None
    )

    assert result is None


def test_get_transcript_text_formats_messages_in_order(db_session, seeded_astrologer):
    session = chat_session_service.get_or_create_session(db_session, "sess-6", seeded_astrologer.id)
    chat_session_service.record_message(db_session, session, role="astrologer", text="My payout is late")
    chat_session_service.record_message(
        db_session, session, role="assistant", text="Let me check that for you"
    )

    transcript = chat_session_service.get_transcript_text(db_session, "sess-6")

    assert transcript == (
        "Astrologer: My payout is late\n\nAssistant: Let me check that for you"
    )


def test_get_transcript_text_returns_none_without_a_session_id(db_session):
    assert chat_session_service.get_transcript_text(db_session, None) is None


def test_get_transcript_text_returns_none_for_an_unknown_session(db_session):
    assert chat_session_service.get_transcript_text(db_session, "no-such-session") is None


def test_get_transcript_text_returns_none_when_no_messages_were_recorded(db_session, seeded_astrologer):
    chat_session_service.get_or_create_session(db_session, "sess-7", seeded_astrologer.id)

    assert chat_session_service.get_transcript_text(db_session, "sess-7") is None
