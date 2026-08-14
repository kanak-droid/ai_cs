from app.integrations import queue_performance_client
from app.models.astrologer import Astrologer
from app.models.expert_priority import ExpertPriority
from app.models.sheet_sync import SheetQueuePerformance


def _linked_astrologer(db_session, expert_id: int) -> Astrologer:
    astrologer = Astrologer(name="Linked", phone="+91-1", language="Hindi", expert_id=expert_id)
    db_session.add(astrologer)
    db_session.commit()
    return astrologer


def test_prefers_expert_priority_over_the_old_frozen_sheet(db_session):
    astrologer = _linked_astrologer(db_session, expert_id=501)
    db_session.add(ExpertPriority(expert_id=501, expert_name="X", current_priority_tier="P2", priority=2))
    db_session.add(
        SheetQueuePerformance(
            expert_id=501,
            expert_name="X",
            priority=5,  # stale — must be ignored in favor of ExpertPriority
            languages="Hindi",
            users_connected=10,
            queues_connected=2,
            total_talktime_min=100,
        )
    )
    db_session.commit()

    result = queue_performance_client.get_queue_performance(db_session, astrologer.id)

    assert result.priority == 2
    # Non-priority stats still come from the (frozen) sheet — unaffected.
    assert result.users_connected == 10


def test_falls_back_to_the_old_sheet_when_not_in_the_new_priority_source(db_session):
    astrologer = _linked_astrologer(db_session, expert_id=502)
    db_session.add(
        SheetQueuePerformance(
            expert_id=502,
            expert_name="Y",
            priority=4,
            languages="Tamil",
            users_connected=5,
            queues_connected=1,
            total_talktime_min=50,
        )
    )
    db_session.commit()

    result = queue_performance_client.get_queue_performance(db_session, astrologer.id)

    assert result.priority == 4


def test_unranked_in_new_source_is_none_not_fabricated(db_session):
    # PRE_MATURE/blank in the real query -> ExpertPriority.priority is None.
    # Must stay None, never silently fall back to a stale sheet number or a
    # fabricated mock value, when the astrologer genuinely has a real (if
    # unranked) row in the new source.
    astrologer = _linked_astrologer(db_session, expert_id=503)
    db_session.add(
        ExpertPriority(expert_id=503, expert_name="Z", current_priority_tier="PRE_MATURE", priority=None)
    )
    db_session.add(
        SheetQueuePerformance(
            expert_id=503,
            expert_name="Z",
            priority=3,
            languages="Telugu",
            users_connected=1,
            queues_connected=1,
            total_talktime_min=10,
        )
    )
    db_session.commit()

    result = queue_performance_client.get_queue_performance(db_session, astrologer.id)

    assert result.priority is None
