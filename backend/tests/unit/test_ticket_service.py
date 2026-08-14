from datetime import timedelta

import pytest

from app.core.errors import AppError
from app.core.time import utcnow
from app.integrations import admin_mapping_client, queue_performance_client
from app.integrations.queue_performance_client import QueuePerformance
from app.models.admin import Admin
from app.models.enums import AdminRole, TicketStatus
from app.models.slack_log import SlackLog
from app.services import ticket_service


def _force_priority(monkeypatch, priority: int) -> None:
    # Routing depends on the astrologer's priority tier — forcing it makes
    # these tests deterministic instead of depending on whatever an
    # auto-incremented test astrologer_id's mock priority happens to be.
    def fake_get_queue_performance(db, astrologer_id):
        return QueuePerformance(
            astrologer_id=astrologer_id,
            priority=priority,
            users_connected=0,
            queues_connected=0,
            total_talktime_min=0,
        )

    monkeypatch.setattr(queue_performance_client, "get_queue_performance", fake_get_queue_performance)


def _make_resolved_ticket(db_session, seeded_astrologer):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="technical",
        sub_category="app_crash",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )
    return ticket_service.transition_status(
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example"
    )


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


def test_vip_priority_ticket_tags_kam(db_session, seeded_astrologer, seeded_admin, monkeypatch):
    _force_priority(monkeypatch, priority=1)

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="technical",
        sub_category="app_crash",
        description="App crashes on login",
        description_en="App crashes on login",
        preferred_language="English",
    )

    entry = db_session.query(SlackLog).filter_by(ticket_id=ticket.id).one()
    assert "tech team" in entry.message
    assert f"@{seeded_admin.name}" in entry.message


def test_non_vip_priority_ticket_does_not_tag_kam(db_session, seeded_astrologer, monkeypatch):
    # P3+ tickets still go to the shared CS channel and are still assigned
    # to a KAM internally, but the KAM isn't specially paged for them.
    _force_priority(monkeypatch, priority=3)

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="technical",
        sub_category="app_crash",
        description="App crashes on login",
        description_en="App crashes on login",
        preferred_language="English",
    )

    entry = db_session.query(SlackLog).filter_by(ticket_id=ticket.id).one()
    assert "tech team" in entry.message
    assert "@" not in entry.message


def test_unranked_priority_is_never_vip(db_session, seeded_astrologer, monkeypatch):
    # An astrologer with no priority tier yet (e.g. PRE_MATURE in the real
    # priority query) must never be treated as VIP just because `None` sorts
    # oddly against an int — see queue_performance_client.QueuePerformance.
    _force_priority(monkeypatch, priority=None)

    assert ticket_service.is_vip_priority(db_session, seeded_astrologer.id) is False


def test_slack_notification_routes_business_categories_to_business_team(
    db_session, seeded_astrologer, monkeypatch
):
    _force_priority(monkeypatch, priority=3)

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="payout",
        sub_category="payout_delay",
        description="Payout delayed",
        description_en="Payout delayed",
        preferred_language="English",
    )

    entry = db_session.query(SlackLog).filter_by(ticket_id=ticket.id).one()
    assert "business team" in entry.message


def test_vip_no_visibility_ticket_routes_directly_to_kam_channel(
    db_session, seeded_astrologer, seeded_admin, monkeypatch
):
    _force_priority(monkeypatch, priority=2)

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="no_visibility",
        sub_category="low_bookings",
        description="Not getting bookings",
        description_en="Not getting bookings",
        preferred_language="English",
    )

    entry = db_session.query(SlackLog).filter_by(ticket_id=ticket.id).one()
    assert entry.channel == seeded_admin.slack_channel
    assert "directly to you as their KAM" in entry.message


def test_non_vip_no_visibility_ticket_still_uses_shared_channel(
    db_session, seeded_astrologer, seeded_admin, monkeypatch
):
    _force_priority(monkeypatch, priority=4)

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="no_visibility",
        sub_category="low_bookings",
        description="Not getting bookings",
        description_en="Not getting bookings",
        preferred_language="English",
    )

    entry = db_session.query(SlackLog).filter_by(ticket_id=ticket.id).one()
    assert entry.channel != seeded_admin.slack_channel


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


def test_record_satisfaction_closes_ticket_when_satisfied(db_session, seeded_astrologer):
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)

    ticket = ticket_service.record_satisfaction(db_session, ticket, satisfied=True)

    assert ticket.status == TicketStatus.CLOSED
    assert ticket.satisfaction == "satisfied"


def test_record_satisfaction_reopens_ticket_when_unsatisfied(db_session, seeded_astrologer):
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)

    ticket = ticket_service.record_satisfaction(db_session, ticket, satisfied=False)

    assert ticket.status == TicketStatus.UNDER_REVIEW
    assert ticket.satisfaction == "unsatisfied"


def test_record_satisfaction_rejects_ticket_not_awaiting_response(db_session, seeded_astrologer):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    with pytest.raises(AppError):
        ticket_service.record_satisfaction(db_session, ticket, satisfied=True)


def test_resolving_a_ticket_clears_any_earlier_satisfaction(db_session, seeded_astrologer):
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)
    ticket = ticket_service.record_satisfaction(db_session, ticket, satisfied=False)
    assert ticket.satisfaction == "unsatisfied"

    ticket = ticket_service.transition_status(
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example"
    )

    assert ticket.satisfaction is None


def test_stale_resolved_ticket_auto_closes_after_5_days(db_session, seeded_astrologer):
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)
    ticket.resolved_at = utcnow() - timedelta(days=6)
    db_session.commit()

    ticket = ticket_service.get_ticket_for_astrologer(db_session, ticket.id, seeded_astrologer.id)

    assert ticket.status == TicketStatus.CLOSED
    assert ticket.history[-1].changed_by == "system"


def test_recently_resolved_ticket_does_not_auto_close(db_session, seeded_astrologer):
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)

    ticket = ticket_service.get_ticket_for_astrologer(db_session, ticket.id, seeded_astrologer.id)

    assert ticket.status == TicketStatus.RESOLVED


def test_list_all_tickets_filters_by_status_and_admin(db_session, seeded_astrologer, monkeypatch):
    # Forced VIP so kam_notified is deterministically true — this test is
    # about the status/admin filter itself, not the notified-gating logic
    # (see test_list_all_tickets_excludes_a_kam_never_actually_notified).
    _force_priority(monkeypatch, priority=1)

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


def test_cs_admins_are_never_round_robin_assigned(db_session, seeded_admin):
    # seeded_admin is a KAM by default; add a CS admin alongside it and make
    # sure round-robin assignment never lands on the CS one.
    cs_admin = Admin(
        name="CS Person", email="cs@test.example", password_hash="x", role=AdminRole.CS
    )
    db_session.add(cs_admin)
    db_session.commit()

    for astrologer_id in range(1, 6):
        assignment = admin_mapping_client.get_assigned_admin(db_session, astrologer_id)
        assert assignment.admin_id == seeded_admin.id


def test_inactive_admins_are_never_round_robin_assigned(db_session, seeded_admin):
    seeded_admin.is_active = False
    other_kam = Admin(
        name="Other KAM", email="other-kam@test.example", password_hash="x", role=AdminRole.KAM
    )
    db_session.add(other_kam)
    db_session.commit()

    assignment = admin_mapping_client.get_assigned_admin(db_session, astrologer_id=1)

    assert assignment.admin_id == other_kam.id


def test_kam_round_robin_matches_the_astrologers_language(db_session, seeded_astrologer):
    # seeded_astrologer's language is "Hindi" (see conftest.seeded_astrologer).
    hindi_kam = Admin(
        name="Hindi KAM", email="hindi-kam@test.example", role=AdminRole.KAM, languages=["Hindi"]
    )
    tamil_kam = Admin(
        name="Tamil KAM", email="tamil-kam@test.example", role=AdminRole.KAM, languages=["Tamil"]
    )
    db_session.add_all([hindi_kam, tamil_kam])
    db_session.commit()

    assignment = admin_mapping_client.get_assigned_admin(db_session, seeded_astrologer.id)

    assert assignment.admin_id == hindi_kam.id


def test_kam_round_robin_falls_back_to_full_pool_when_no_kam_matches_the_language(
    db_session, seeded_astrologer, seeded_admin
):
    # seeded_astrologer speaks Hindi; no active KAM here covers it, so the
    # only active KAM (regardless of language) still gets it.
    seeded_admin.languages = ["Tamil"]
    unmatched_but_inactive = Admin(
        name="Inactive Tamil KAM",
        email="inactive-tamil-kam@test.example",
        role=AdminRole.KAM,
        languages=["Tamil"],
        is_active=False,
    )
    db_session.add(unmatched_but_inactive)
    db_session.commit()

    assignment = admin_mapping_client.get_assigned_admin(db_session, seeded_astrologer.id)

    assert assignment.admin_id == seeded_admin.id


def test_create_ticket_assigns_a_cs_matching_the_astrologers_language(db_session, seeded_astrologer):
    # seeded_astrologer's language is "Hindi" (see conftest.seeded_astrologer).
    hindi_cs = Admin(
        name="Hindi CS", email="hindi-cs@test.example", role=AdminRole.CS, languages=["Hindi"]
    )
    tamil_cs = Admin(
        name="Tamil CS", email="tamil-cs@test.example", role=AdminRole.CS, languages=["Tamil"]
    )
    db_session.add_all([hindi_cs, tamil_cs])
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

    assert ticket.assigned_cs_id == hindi_cs.id


def test_create_ticket_leaves_assigned_cs_null_when_no_cs_admins_exist(db_session, seeded_astrologer):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    assert ticket.assigned_cs_id is None


def test_list_all_tickets_filter_matches_either_kam_or_cs_assignment(db_session, seeded_astrologer):
    hindi_cs = Admin(
        name="Hindi CS 2", email="hindi-cs-2@test.example", role=AdminRole.CS, languages=["Hindi"]
    )
    db_session.add(hindi_cs)
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
    assert ticket.assigned_cs_id == hindi_cs.id

    results = ticket_service.list_all_tickets(db_session, assigned_admin_id=hindi_cs.id)

    assert [t.id for t in results] == [ticket.id]


def test_photo_change_ticket_requires_a_photo(db_session, seeded_astrologer):
    assert ticket_service.needs_evidence("profile") is True


def test_photo_change_routes_directly_to_kam_regardless_of_priority(
    db_session, seeded_astrologer, seeded_admin, monkeypatch
):
    for priority in (1, 5):
        _force_priority(monkeypatch, priority=priority)
        ticket = ticket_service.create_ticket(
            db_session,
            astrologer_id=seeded_astrologer.id,
            category="profile",
            sub_category="photo_change",
            description="beautified photo",
            description_en="beautified photo",
            preferred_language="English",
            attachment_url="http://x/beautified.jpg",
        )

        # Two rows now: the text notification, and the attachment-upload
        # log (create_ticket also pushes the photo into Slack — see
        # slack_client.upload_attachment).
        entries = db_session.query(SlackLog).filter_by(ticket_id=ticket.id).all()
        assert len(entries) == 2
        text_entry = next(e for e in entries if "directly to you as their KAM" in e.message)
        assert text_entry.channel == seeded_admin.slack_channel
        assert ticket.kam_notified is True
        # Photo Change is KAM-only per policy — CS is never looped in, even
        # though a CS may still be recorded as assigned_cs_id.
        assert ticket.cs_notified is False
        assert "*CS:*" not in text_entry.message


def test_list_all_tickets_excludes_a_kam_never_actually_notified(
    db_session, seeded_astrologer, seeded_admin, monkeypatch
):
    # Reproduces the real dashboard confusion: a low-priority astrologer's
    # "no_visibility" ticket never actually notifies their KAM (only CS), so
    # it shouldn't show up when the dashboard filters to that KAM.
    hindi_cs = Admin(
        name="Hindi CS 3", email="hindi-cs-3@test.example", role=AdminRole.CS, languages=["Hindi"]
    )
    db_session.add(hindi_cs)
    db_session.commit()

    _force_priority(monkeypatch, priority=5)
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="no_visibility",
        sub_category="low_bookings",
        description="Not getting bookings",
        description_en="Not getting bookings",
        preferred_language="English",
    )
    assert ticket.assigned_admin_id == seeded_admin.id
    assert ticket.kam_notified is False

    kam_results = ticket_service.list_all_tickets(db_session, assigned_admin_id=seeded_admin.id)
    assert ticket.id not in [t.id for t in kam_results]

    cs_results = ticket_service.list_all_tickets(db_session, assigned_admin_id=hindi_cs.id)
    assert ticket.id in [t.id for t in cs_results]


def test_list_all_tickets_includes_a_vip_notified_kam(
    db_session, seeded_astrologer, seeded_admin, monkeypatch
):
    _force_priority(monkeypatch, priority=1)
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="no_visibility",
        sub_category="low_bookings",
        description="Not getting bookings",
        description_en="Not getting bookings",
        preferred_language="English",
    )
    assert ticket.kam_notified is True

    results = ticket_service.list_all_tickets(db_session, assigned_admin_id=seeded_admin.id)

    assert ticket.id in [t.id for t in results]


def test_list_all_tickets_sort_priority_orders_most_urgent_first(db_session, seeded_admin, monkeypatch):
    from app.models.astrologer import Astrologer

    low = Astrologer(name="Low Prio", phone="+91-1", language="English")
    high = Astrologer(name="High Prio", phone="+91-2", language="English")
    mid = Astrologer(name="Mid Prio", phone="+91-3", language="English")
    db_session.add_all([low, high, mid])
    db_session.commit()

    priorities = {low.id: 5, high.id: 1, mid.id: 3}

    def fake_get_queue_performance(db, astrologer_id):
        return QueuePerformance(
            astrologer_id=astrologer_id,
            priority=priorities[astrologer_id],
            users_connected=0,
            queues_connected=0,
            total_talktime_min=0,
        )

    monkeypatch.setattr(queue_performance_client, "get_queue_performance", fake_get_queue_performance)

    tickets = {}
    for astrologer in (low, high, mid):
        tickets[astrologer.id] = ticket_service.create_ticket(
            db_session,
            astrologer_id=astrologer.id,
            category="other",
            sub_category="general",
            description="issue",
            description_en="issue",
            preferred_language="English",
        )

    results = ticket_service.list_all_tickets(db_session, sort="priority")
    ordered_ids = [t.astrologer_id for t in results]

    assert ordered_ids.index(high.id) < ordered_ids.index(mid.id) < ordered_ids.index(low.id)


def test_list_all_tickets_sort_priority_places_unranked_last(db_session, seeded_admin, monkeypatch):
    from app.models.astrologer import Astrologer

    ranked = Astrologer(name="Ranked", phone="+91-4", language="English")
    unranked = Astrologer(name="Unranked", phone="+91-5", language="English")
    db_session.add_all([ranked, unranked])
    db_session.commit()

    priorities = {ranked.id: 1, unranked.id: None}

    def fake_get_queue_performance(db, astrologer_id):
        return QueuePerformance(
            astrologer_id=astrologer_id,
            priority=priorities[astrologer_id],
            users_connected=0,
            queues_connected=0,
            total_talktime_min=0,
        )

    monkeypatch.setattr(queue_performance_client, "get_queue_performance", fake_get_queue_performance)

    for astrologer in (unranked, ranked):
        ticket_service.create_ticket(
            db_session,
            astrologer_id=astrologer.id,
            category="other",
            sub_category="general",
            description="issue",
            description_en="issue",
            preferred_language="English",
        )

    results = ticket_service.list_all_tickets(db_session, sort="priority")
    ordered_ids = [t.astrologer_id for t in results]

    assert ordered_ids.index(ranked.id) < ordered_ids.index(unranked.id)


def test_attach_astrologer_priority_sets_it_per_astrologer(db_session, seeded_astrologer, monkeypatch):
    _force_priority(monkeypatch, priority=2)

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )
    assert not hasattr(ticket.astrologer, "priority")

    ticket_service.attach_astrologer_priority(db_session, [ticket])

    assert ticket.astrologer.priority == 2
