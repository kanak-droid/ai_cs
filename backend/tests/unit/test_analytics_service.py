from datetime import date, datetime

from app.integrations import queue_performance_client
from app.integrations.queue_performance_client import QueuePerformance
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
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed"
    )
    ticket_service.record_ticket_rating(db_session, ticket, rating=5, reasons=["Quick response"], comment=None)

    overview = analytics_service.get_overview(db_session)

    assert overview["satisfied_count"] >= 1
    assert overview["avg_ticket_rating"] is not None
    assert overview["ticket_rating_distribution"].get("5", 0) >= 1


def test_overview_averages_bot_feedback_rating(db_session, seeded_astrologer):
    chat_session_service.get_or_create_session(db_session, "an-rating-1", seeded_astrologer.id)
    chat_session_service.record_feedback(
        db_session, "an-rating-1", seeded_astrologer.id, rating=4, comment=None
    )

    overview = analytics_service.get_overview(db_session)

    assert overview["avg_bot_rating"] is not None
    assert overview["rating_distribution"].get("4", 0) >= 1


def test_list_ticket_ratings_returns_individual_entries(db_session, seeded_astrologer):
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
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed"
    )
    ticket_service.record_ticket_rating(
        db_session, ticket, rating=2, reasons=["Took too long"], comment="Still slow"
    )

    entries = analytics_service.list_ticket_ratings(db_session)

    matching = [e for e in entries if e["ticket_id"] == ticket.id]
    assert len(matching) == 1
    assert matching[0]["rating"] == 2
    assert matching[0]["reasons"] == ["Took too long"]
    assert matching[0]["comment"] == "Still slow"
    assert matching[0]["astrologer_name"] == seeded_astrologer.name


def test_kam_performance_counts_pending_assigned_and_solved(
    db_session, seeded_astrologer, seeded_admin
):
    pending = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="still open",
        description_en="still open",
        preferred_language="English",
    )
    solved = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="will be resolved",
        description_en="will be resolved",
        preferred_language="English",
    )
    ticket_service.transition_status(
        db_session, solved, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed"
    )

    overview = analytics_service.get_overview(db_session)

    row = next(r for r in overview["kam_performance"] if r["admin_id"] == seeded_admin.id)
    assert row["assigned_count"] == 2
    assert row["pending_count"] == 1
    assert row["solved_count"] == 1
    assert row["avg_tat_hours"] is not None


def test_priority_filter_only_counts_matching_astrologers(db_session, seeded_admin, monkeypatch):
    from app.models.astrologer import Astrologer

    p1_astrologer = Astrologer(
        name="P1", phone="+91-1", language="English", assigned_admin_id=seeded_admin.id
    )
    p3_astrologer = Astrologer(
        name="P3", phone="+91-2", language="English", assigned_admin_id=seeded_admin.id
    )
    db_session.add_all([p1_astrologer, p3_astrologer])
    db_session.commit()

    def fake_priority(db, astrologer_id):
        priority = 1 if astrologer_id == p1_astrologer.id else 3
        return QueuePerformance(
            astrologer_id=astrologer_id,
            priority=priority,
            users_connected=0,
            queues_connected=0,
            total_talktime_min=0,
        )

    monkeypatch.setattr(queue_performance_client, "get_queue_performance", fake_priority)

    chat_session_service.get_or_create_session(db_session, "p1-session", p1_astrologer.id)
    chat_session_service.mark_resolved_by_bot(
        db_session, "p1-session", category="payout", sub_category="payout_delay"
    )
    chat_session_service.get_or_create_session(db_session, "p3-session", p3_astrologer.id)
    chat_session_service.mark_resolved_by_bot(
        db_session, "p3-session", category="kyc", sub_category="kyc_rejected"
    )
    db_session.commit()

    p1_overview = analytics_service.get_overview(db_session, priority="1")
    p1_categories = {c["category"] for c in p1_overview["top_categories"]}
    assert "payout" in p1_categories
    assert "kyc" not in p1_categories

    p3_overview = analytics_service.get_overview(db_session, priority="3")
    p3_categories = {c["category"] for c in p3_overview["top_categories"]}
    assert "kyc" in p3_categories
    assert "payout" not in p3_categories


def test_date_range_excludes_sessions_and_tickets_outside_it(db_session, seeded_astrologer):
    old_session = chat_session_service.get_or_create_session(db_session, "old-session", seeded_astrologer.id)
    chat_session_service.mark_resolved_by_bot(
        db_session, "old-session", category="payout", sub_category="payout_delay"
    )
    old_session.started_at = datetime(2026, 1, 5)

    new_session = chat_session_service.get_or_create_session(db_session, "new-session", seeded_astrologer.id)
    chat_session_service.mark_resolved_by_bot(
        db_session, "new-session", category="kyc", sub_category="kyc_rejected"
    )
    new_session.started_at = datetime(2026, 8, 10)
    db_session.commit()

    overview = analytics_service.get_overview(
        db_session, date_from=date(2026, 8, 1), date_to=date(2026, 8, 31)
    )
    categories = {c["category"] for c in overview["top_categories"]}
    assert "kyc" in categories
    assert "payout" not in categories


def test_kam_performance_respects_date_range(db_session, seeded_astrologer, seeded_admin):
    old_ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="old one",
        description_en="old one",
        preferred_language="English",
    )
    old_ticket.created_at = datetime(2026, 1, 5)
    db_session.commit()

    overview = analytics_service.get_overview(
        db_session, date_from=date(2026, 8, 1), date_to=date(2026, 8, 31)
    )
    row = next(r for r in overview["kam_performance"] if r["admin_id"] == seeded_admin.id)
    assert row["assigned_count"] == 0


def test_escalated_ticket_is_excluded_from_the_cs_solved_tally(
    db_session, seeded_astrologer, seeded_admin
):
    from app.models.admin import Admin
    from app.models.enums import AdminRole

    cs_admin = Admin(name="CS One", email="csone@test.example", role=AdminRole.CS)
    db_session.add(cs_admin)
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
    assert ticket.assigned_cs_id == cs_admin.id  # sanity check: only CS in the pool

    ticket_service.escalate_to_kam(db_session, ticket, changed_by="cs@test.example", note="Needs KAM")
    ticket_service.transition_status(
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed"
    )

    overview = analytics_service.get_overview(db_session)

    cs_row = next(r for r in overview["kam_performance"] if r["admin_id"] == cs_admin.id)
    assert cs_row["solved_count"] == 0
    assert cs_row["escalated_to_kam_count"] == 1

    # The KAM legitimately resolved it — still counts for them.
    kam_row = next(r for r in overview["kam_performance"] if r["admin_id"] == seeded_admin.id)
    assert kam_row["solved_count"] == 1
    assert kam_row["escalated_to_kam_count"] == 0


def test_weekly_and_monthly_ticket_trend_bucket_by_created_date(db_session, seeded_astrologer):
    same_week_a = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="a",
        description_en="a",
        preferred_language="English",
    )
    same_week_a.created_at = datetime(2026, 8, 10)  # Monday
    same_week_b = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="b",
        description_en="b",
        preferred_language="English",
    )
    same_week_b.created_at = datetime(2026, 8, 12)  # same week
    next_month = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="c",
        description_en="c",
        preferred_language="English",
    )
    next_month.created_at = datetime(2026, 9, 3)
    db_session.commit()

    overview = analytics_service.get_overview(
        db_session, date_from=date(2026, 8, 1), date_to=date(2026, 9, 30)
    )

    weekly = {row["period"]: row["created_count"] for row in overview["weekly_ticket_trend"]}
    assert weekly.get("2026-08-10") == 2

    monthly = {row["period"]: row["created_count"] for row in overview["monthly_ticket_trend"]}
    assert monthly.get("2026-08-01") == 2
    assert monthly.get("2026-09-01") == 1
