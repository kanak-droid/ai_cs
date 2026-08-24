from datetime import timedelta

import pytest

from app.core.errors import AppError
from app.core.time import utcnow
from app.integrations import admin_mapping_client, moengage_client, queue_performance_client
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
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed the issue"
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


def test_vip_priority_ticket_uses_a_real_slack_mention_when_the_kam_has_one_on_file(
    db_session, seeded_astrologer, seeded_admin, monkeypatch
):
    # Plain "@name" text in an incoming webhook message is never rendered as
    # a real, notifying Slack mention — only <@SLACK_USER_ID> is. Confirmed
    # this was silently never paging anyone (2026-08-18).
    seeded_admin.slack_user_id = "U0123ABC456"
    db_session.commit()
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
    assert "<@U0123ABC456>" in entry.message
    assert f"@{seeded_admin.name}" not in entry.message


def test_direct_to_kam_ticket_names_the_kam_explicitly_in_slack(
    db_session, seeded_astrologer, seeded_admin, monkeypatch
):
    # Confirmed live 2026-08-19: "profile" (photo_change) tickets go
    # straight to the KAM's own slack_channel with no explicit name/mention
    # in the text — fine ONLY if that channel is genuinely personal, but
    # none of the real KAMs had ever been given one (all still on the
    # Admin model's shared "#support" default), so the message named no
    # one and pinged no one. Must always name the KAM regardless of
    # whether the channel is actually personal.
    seeded_admin.slack_user_id = "U0123ABC456"
    db_session.commit()
    _force_priority(monkeypatch, priority=5)  # low priority — must still go direct for "profile"

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="profile",
        sub_category="photo_change",
        description="Wants a new profile photo",
        description_en="Wants a new profile photo",
        preferred_language="English",
    )

    entry = db_session.query(SlackLog).filter_by(ticket_id=ticket.id).one()
    assert "<@U0123ABC456>" in entry.message
    assert "Routed directly to you as their KAM" not in entry.message


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
    assert f"directly to @{seeded_admin.name} as their KAM" in entry.message


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


def test_a_moengage_failure_never_blocks_a_status_transition(db_session, seeded_astrologer, monkeypatch):
    # _record_status is the one choke point for every ticket status write in
    # the app — a bug or outage in the MoEngage event dispatch it now also
    # does must never be able to take a real status transition down with it.
    def _boom(*args, **kwargs):
        raise RuntimeError("MoEngage is down")

    monkeypatch.setattr(moengage_client, "send_ticket_status_event", _boom)

    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    ticket = ticket_service.transition_status(
        db_session, ticket, TicketStatus.IN_PROGRESS, changed_by="admin@test.example"
    )

    assert ticket.status == TicketStatus.IN_PROGRESS


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

    # CLOSED isn't in this loop — it's no longer a manually-settable status
    # (see ADMIN_SETTABLE_STATUSES); only record_ticket_rating/auto-close can
    # reach it now, covered by their own tests below.
    for status in (TicketStatus.UNDER_REVIEW, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED):
        note = "Fixed the issue" if status == TicketStatus.RESOLVED else None
        ticket = ticket_service.transition_status(
            db_session, ticket, status, changed_by="admin@test.example", note=note
        )
        assert ticket.status == status
        assert ticket.history[-1].status == status


def test_record_ticket_rating_closes_ticket_when_rating_is_high(db_session, seeded_astrologer):
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)

    ticket = ticket_service.record_ticket_rating(
        db_session, ticket, rating=5, reasons=["Quick response"], comment=None
    )

    assert ticket.status == TicketStatus.CLOSED
    assert ticket.satisfaction == "satisfied"
    assert ticket.rating == 5
    assert ticket.rating_reasons == ["Quick response"]
    assert ticket.rated_at is not None


def test_record_ticket_rating_reopens_ticket_when_rating_is_low(db_session, seeded_astrologer):
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)

    ticket = ticket_service.record_ticket_rating(
        db_session, ticket, rating=2, reasons=["Took too long"], comment="Still broken"
    )

    assert ticket.status == TicketStatus.UNDER_REVIEW
    assert ticket.satisfaction == "unsatisfied"
    assert ticket.rating == 2
    assert ticket.rating_comment == "Still broken"


def test_record_ticket_rating_of_exactly_four_counts_as_satisfied(db_session, seeded_astrologer):
    # The user-facing threshold is ">=4 stars" — 4 itself must close, not
    # just 5, since the astrologer never sees "4 means unsatisfied".
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)

    ticket = ticket_service.record_ticket_rating(db_session, ticket, rating=4, reasons=[], comment=None)

    assert ticket.status == TicketStatus.CLOSED
    assert ticket.satisfaction == "satisfied"


def test_record_ticket_rating_rejects_ticket_not_awaiting_response(db_session, seeded_astrologer):
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
        ticket_service.record_ticket_rating(db_session, ticket, rating=5, reasons=[], comment=None)


def test_resolving_a_ticket_clears_any_earlier_rating(db_session, seeded_astrologer):
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)
    ticket = ticket_service.record_ticket_rating(
        db_session, ticket, rating=2, reasons=["Took too long"], comment="not fixed"
    )
    assert ticket.satisfaction == "unsatisfied"

    ticket = ticket_service.transition_status(
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed again"
    )

    assert ticket.satisfaction is None
    assert ticket.rating is None
    assert ticket.rating_reasons is None
    assert ticket.rating_comment is None
    assert ticket.rated_at is None


def test_stale_resolved_ticket_auto_closes_after_48_hours(db_session, seeded_astrologer):
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)
    ticket.resolved_at = utcnow() - timedelta(hours=49)
    db_session.commit()

    ticket = ticket_service.get_ticket_for_astrologer(db_session, ticket.id, seeded_astrologer.id)

    assert ticket.status == TicketStatus.CLOSED
    assert ticket.history[-1].changed_by == "system"


def test_admin_reading_a_stale_resolved_ticket_also_auto_closes_it(db_session, seeded_astrologer):
    # The lazy check used to only run on the astrologer-facing read path —
    # an admin viewing the same ticket must see it correctly closed too,
    # regardless of whether the astrologer's app has polled recently.
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)
    ticket.resolved_at = utcnow() - timedelta(hours=49)
    db_session.commit()

    ticket = ticket_service.get_ticket(db_session, ticket.id)

    assert ticket.status == TicketStatus.CLOSED


def test_recently_resolved_ticket_does_not_auto_close(db_session, seeded_astrologer):
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)

    ticket = ticket_service.get_ticket_for_astrologer(db_session, ticket.id, seeded_astrologer.id)

    assert ticket.status == TicketStatus.RESOLVED


def test_auto_close_stale_resolved_tickets_closes_only_eligible_ones(db_session, seeded_astrologer):
    stale = _make_resolved_ticket(db_session, seeded_astrologer)
    stale.resolved_at = utcnow() - timedelta(hours=49)
    fresh = _make_resolved_ticket(db_session, seeded_astrologer)
    db_session.commit()

    closed = ticket_service.auto_close_stale_resolved_tickets(db_session)

    assert [t.id for t in closed] == [stale.id]
    db_session.refresh(stale)
    db_session.refresh(fresh)
    assert stale.status == TicketStatus.CLOSED
    assert fresh.status == TicketStatus.RESOLVED


def test_transition_status_rejects_a_status_not_manually_settable(db_session, seeded_astrologer):
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
        ticket_service.transition_status(
            db_session, ticket, TicketStatus.CLOSED, changed_by="admin@test.example"
        )
    with pytest.raises(AppError):
        ticket_service.transition_status(
            db_session, ticket, TicketStatus.SUBMITTED, changed_by="admin@test.example"
        )


def test_transition_status_requires_a_comment_to_resolve(db_session, seeded_astrologer):
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
        ticket_service.transition_status(
            db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example"
        )
    with pytest.raises(AppError):
        ticket_service.transition_status(
            db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="   "
        )
    # A real comment succeeds.
    ticket = ticket_service.transition_status(
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed it"
    )
    assert ticket.status == TicketStatus.RESOLVED


def test_get_active_ticket_for_category_finds_an_open_ticket(db_session, seeded_astrologer):
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="technical",
        sub_category="app_crash",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    found = ticket_service.get_active_ticket_for_category(
        db_session, seeded_astrologer.id, "technical"
    )

    assert found is not None
    assert found.id == ticket.id


def test_get_active_ticket_for_category_ignores_resolved_and_closed(db_session, seeded_astrologer):
    ticket = _make_resolved_ticket(db_session, seeded_astrologer)
    # CLOSED is no longer a manually-settable status — reach it the same
    # way a real ticket does now, via the astrologer confirming it's fixed.
    ticket_service.record_ticket_rating(db_session, ticket, rating=5, reasons=[], comment=None)

    found = ticket_service.get_active_ticket_for_category(
        db_session, seeded_astrologer.id, "technical"
    )

    assert found is None


def test_get_active_ticket_for_category_ignores_a_different_category(db_session, seeded_astrologer):
    ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="technical",
        sub_category="app_crash",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    found = ticket_service.get_active_ticket_for_category(db_session, seeded_astrologer.id, "payout")

    assert found is None


def test_get_active_ticket_for_category_ignores_a_different_astrologer(
    db_session, seeded_astrologer, seeded_admin
):
    from app.models.astrologer import Astrologer

    other = Astrologer(
        name="Other Astrologer",
        phone="+91-90000-00002",
        language="English",
        assigned_admin_id=seeded_admin.id,
    )
    db_session.add(other)
    db_session.commit()
    ticket_service.create_ticket(
        db_session,
        astrologer_id=other.id,
        category="technical",
        sub_category="app_crash",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )

    found = ticket_service.get_active_ticket_for_category(
        db_session, seeded_astrologer.id, "technical"
    )

    assert found is None


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
        db_session, t1, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed"
    )

    results = ticket_service.list_all_tickets(db_session, status=TicketStatus.RESOLVED)
    assert [t.id for t in results] == [t1.id]

    results = ticket_service.list_all_tickets(db_session, status=TicketStatus.CLOSED)
    assert results == []

    results = ticket_service.list_all_tickets(
        db_session, assigned_admin_id=t1.assigned_admin_id
    )
    assert t1.id in [t.id for t in results]


def test_list_all_tickets_filters_by_date_range(db_session, seeded_astrologer):
    from datetime import date, datetime

    old = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="old one",
        description_en="old one",
        preferred_language="English",
    )
    old.created_at = datetime(2026, 1, 5)
    in_range = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="in range",
        description_en="in range",
        preferred_language="English",
    )
    in_range.created_at = datetime(2026, 8, 10)
    db_session.commit()

    results = ticket_service.list_all_tickets(
        db_session, date_from=date(2026, 8, 1), date_to=date(2026, 8, 31)
    )

    assert [t.id for t in results] == [in_range.id]

    # A single day range (from == to) must still include that whole day.
    same_day = ticket_service.list_all_tickets(
        db_session, date_from=date(2026, 8, 10), date_to=date(2026, 8, 10)
    )
    assert in_range.id in [t.id for t in same_day]


def test_reassign_ticket_moves_kam_ownership_and_notifies_the_new_kam(
    db_session, seeded_astrologer, seeded_admin
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

    ticket = ticket_service.reassign_ticket(
        db_session,
        ticket,
        role="kam",
        new_admin_id=other_kam.id,
        changed_by="admin@test.example",
        note="Covering for original KAM",
    )

    assert ticket.assigned_admin_id == other_kam.id
    assert ticket.kam_notified is True
    last_entry = ticket.history[-1]
    assert "Other KAM" in last_entry.note
    assert "Covering for original KAM" in last_entry.note


def test_reassign_ticket_rejects_an_admin_of_the_wrong_role(
    db_session, seeded_astrologer, seeded_admin
):
    cs_admin = Admin(name="A CS", email="acs@test.example", role=AdminRole.CS)
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

    with pytest.raises(AppError):
        ticket_service.reassign_ticket(
            db_session, ticket, role="kam", new_admin_id=cs_admin.id, changed_by="admin@test.example"
        )


def test_reassign_ticket_rejects_an_admin_on_leave(db_session, seeded_astrologer, seeded_admin):
    on_leave_kam = Admin(
        name="On Leave KAM",
        email="onleavekam@test.example",
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

    with pytest.raises(AppError):
        ticket_service.reassign_ticket(
            db_session,
            ticket,
            role="kam",
            new_admin_id=on_leave_kam.id,
            changed_by="admin@test.example",
        )


def test_reassigning_a_resolved_ticket_does_not_reset_its_resolution(
    db_session, seeded_astrologer, seeded_admin
):
    # A real risk with reusing _record_status for this: on a RESOLVED
    # ticket it resets resolved_at to now and wipes satisfaction as a side
    # effect — a mere ownership change must never trigger that. See
    # ticket_service._log_note.
    other_kam = Admin(name="Other KAM", email="otherkam2@test.example", role=AdminRole.KAM)
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
    ticket = ticket_service.transition_status(
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed it"
    )
    ticket = ticket_service.record_ticket_rating(
        db_session, ticket, rating=2, reasons=[], comment=None
    )  # reopens to under_review
    ticket = ticket_service.transition_status(
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed it again"
    )
    original_resolved_at = ticket.resolved_at
    assert ticket.satisfaction is None

    ticket = ticket_service.reassign_ticket(
        db_session, ticket, role="kam", new_admin_id=other_kam.id, changed_by="admin@test.example"
    )

    assert ticket.status == TicketStatus.RESOLVED
    assert ticket.resolved_at == original_resolved_at
    assert ticket.satisfaction is None


def test_escalate_to_kam_requires_a_comment(db_session, seeded_astrologer, seeded_admin):
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
        ticket_service.escalate_to_kam(db_session, ticket, changed_by="cs@test.example", note="")
    with pytest.raises(AppError):
        ticket_service.escalate_to_kam(db_session, ticket, changed_by="cs@test.example", note="   ")


def test_escalate_to_kam_flags_the_ticket_and_notifies_the_kam(
    db_session, seeded_astrologer, seeded_admin
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

    ticket = ticket_service.escalate_to_kam(
        db_session, ticket, changed_by="cs@test.example", note="Needs the KAM's relationship here"
    )

    assert ticket.escalated_to_kam is True
    assert ticket.escalated_at is not None
    assert ticket.kam_notified is True
    assert "Needs the KAM's relationship here" in ticket.history[-1].note


def test_escalating_a_resolved_ticket_does_not_reset_its_resolution(
    db_session, seeded_astrologer, seeded_admin
):
    # Same class of risk as reassign_ticket — escalation must never touch
    # resolved_at/satisfaction via _record_status. See ticket_service._log_note.
    ticket = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="issue",
        description_en="issue",
        preferred_language="English",
    )
    ticket = ticket_service.transition_status(
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed"
    )
    original_resolved_at = ticket.resolved_at

    ticket = ticket_service.escalate_to_kam(
        db_session, ticket, changed_by="cs@test.example", note="Actually needs KAM review"
    )

    assert ticket.status == TicketStatus.RESOLVED
    assert ticket.resolved_at == original_resolved_at
    assert ticket.satisfaction is None


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
        text_entry = next(e for e in entries if "as their KAM" in e.message)
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


def test_list_all_tickets_sort_priority_breaks_ties_oldest_first(
    db_session, seeded_astrologer, monkeypatch
):
    from datetime import datetime

    # Same astrologer -> same priority for both tickets, so this isolates
    # the tie-break rule: within a priority tier, whoever's been waiting
    # longest should surface first (not last, which is what a naive
    # newest-first fetch before the stable sort would produce).
    monkeypatch.setattr(
        queue_performance_client,
        "get_queue_performance",
        lambda db, astrologer_id: QueuePerformance(
            astrologer_id=astrologer_id,
            priority=2,
            users_connected=0,
            queues_connected=0,
            total_talktime_min=0,
        ),
    )

    older = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="older issue",
        description_en="older issue",
        preferred_language="English",
    )
    older.created_at = datetime(2026, 8, 1)
    newer = ticket_service.create_ticket(
        db_session,
        astrologer_id=seeded_astrologer.id,
        category="other",
        sub_category="general",
        description="newer issue",
        description_en="newer issue",
        preferred_language="English",
    )
    newer.created_at = datetime(2026, 8, 10)
    db_session.commit()

    results = ticket_service.list_all_tickets(db_session, sort="priority")
    ordered_ids = [t.id for t in results if t.id in (older.id, newer.id)]

    assert ordered_ids == [older.id, newer.id]


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
