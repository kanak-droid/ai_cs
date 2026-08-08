from app.models.enums import TicketStatus
from app.models.slack_log import SlackLog
from app.services import ticket_service


def test_create_ticket_submits_then_auto_assigns(db_session, seeded_astrologer):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="payout",
        sub_category="payout_delay",
        description="mera payout nahi aaya",
        description_en="Astrologer reports a delayed payout",
        preferred_language="Hindi",
    )

    assert ticket.status == TicketStatus.ASSIGNED_TO_KAM
    assert ticket.assigned_admin_id is not None

    statuses = [h.status for h in ticket.history]
    assert statuses == [TicketStatus.SUBMITTED, TicketStatus.ASSIGNED_TO_KAM]


def test_create_ticket_writes_slack_log(db_session, seeded_astrologer):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="kyc",
        sub_category="kyc_rejected",
        description="KYC reject ho gaya",
        description_en="Astrologer's KYC was rejected",
        preferred_language="Hindi",
    )

    entries = db_session.query(SlackLog).filter_by(ticket_id=ticket.id).all()
    assert len(entries) == 1
    assert entries[0].mock is True
    assert f"#{ticket.id}" in entries[0].message


def test_status_always_mirrors_latest_history(db_session, seeded_astrologer):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    for status in (
        TicketStatus.UNDER_REVIEW,
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    ):
        ticket = ticket_service.transition_status(
            db_session, ticket, status, changed_by="admin@test.example"
        )
        assert ticket.status == status
        assert ticket.history[-1].status == status


def test_list_all_tickets_filters_by_status_and_admin(db_session, seeded_astrologer):
    t1 = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="a",
        description_en="a",
        preferred_language="English",
    )
    ticket_service.transition_status(
        db_session, t1, TicketStatus.RESOLVED, changed_by="admin@test.example"
    )

    results = ticket_service.list_all_tickets(db_session, status=TicketStatus.RESOLVED)
    assert [t.id for t in results] == [t1.id]

    results = ticket_service.list_all_tickets(db_session, status=TicketStatus.CLOSED)
    assert results == []

    results = ticket_service.list_all_tickets(
        db_session, assigned_admin_id=t1.assigned_admin_id
    )
    assert t1.id in [t.id for t in results]
