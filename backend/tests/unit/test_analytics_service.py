from app.models.enums import TicketStatus
from app.services import analytics_service, chat_session_service, ticket_service


def test_overview_counts_bot_resolved_and_escalated_sessions(db_session, seeded_astrologer):
    chat_session_service.get_or_create_session(db_session, "an-bot-1", seeded_astrologer.id)
    chat_session_service.mark_resolved_by_bot(
        db_session, "an-bot-1", category="payout", sub_category="payout_delay"
    )
    chat_session_service.get_or_create_session(db_session, "an-esc-1", seeded_astrologer.id)
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="technical",
        sub_category="app_crash",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )
    chat_session_service.mark_escalated(db_session, "an-esc-1", ticket_id=ticket.id)
    db_session.commit()

    overview = analytics_service.get_overview(db_session)

    assert overview["bot_resolved_count"] >= 1
    assert overview["escalated_count"] >= 1
    categories = {c["category"] for c in overview["top_categories"]}
    assert "payout" in categories


def test_overview_counts_ticket_satisfaction(db_session, seeded_astrologer):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="kyc",
        sub_category="kyc_rejected",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )
    ticket = ticket_service.transition_status(
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example"
    )
    ticket_service.record_satisfaction(db_session, ticket, satisfied=True)

    overview = analytics_service.get_overview(db_session)

    assert overview["satisfied_count"] >= 1


def test_overview_averages_bot_feedback_rating(db_session, seeded_astrologer):
    chat_session_service.get_or_create_session(db_session, "an-rating-1", seeded_astrologer.id)
    chat_session_service.record_feedback(
        db_session, "an-rating-1", seeded_astrologer.id, rating=4, comment=None
    )

    overview = analytics_service.get_overview(db_session)

    assert overview["avg_bot_rating"] is not None
    assert overview["rating_distribution"].get("4", 0) >= 1
