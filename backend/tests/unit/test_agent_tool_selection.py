from google.genai import types

from app.agent import executor, orchestrator, tool_schemas
from app.agent.context import SessionContext
from app.agent.orchestrator import MAX_ITERATIONS, HistoryTurn, run_chat_turn
from app.agent.tool_registry import REGISTRY
from app.integrations import payout_client, queue_performance_client
from app.integrations.queue_performance_client import QueuePerformance


def _force_priority(monkeypatch, priority: int) -> None:
    def fake_get_queue_performance(db, astrologer_id):
        return QueuePerformance(
            astrologer_id=astrologer_id,
            priority=priority,
            users_connected=0,
            queues_connected=0,
            total_talktime_min=0,
        )

    monkeypatch.setattr(queue_performance_client, "get_queue_performance", fake_get_queue_performance)


def text_response(text: str) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(content=types.Content(role="model", parts=[types.Part(text=text)]))
        ]
    )


def tool_call_response(name: str, args: dict | None = None) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[types.Part(function_call=types.FunctionCall(name=name, args=args or {}))],
                )
            )
        ]
    )


class FakeAgentClient:
    """Constructor-injected fake — never touches the real Gemini API."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, *, system, contents, tools):
        # Snapshot contents — the orchestrator keeps appending to the same
        # list object after this call, so recording a live reference would
        # make every recorded call reflect the final state, not what was
        # actually sent at the time.
        self.calls.append({"system": system, "contents": list(contents), "tools": tools})
        return self.responses.pop(0)


def make_ctx(db_session, astrologer_id=1) -> SessionContext:
    return SessionContext(astrologer_id=astrologer_id, name="Test", language="English", db=db_session)


def test_orchestrator_sends_prior_history_to_the_model(db_session):
    # Regression test: the backend is stateless across /api/chat requests, so
    # without threading `history` into `contents`, the model would have no
    # memory of anything said earlier — e.g. it couldn't write a ticket
    # summary reflecting the real issue, only the astrologer's latest message.
    ctx = make_ctx(db_session)
    fake_client = FakeAgentClient([text_response("I'll raise a ticket for that.")])
    history = [
        HistoryTurn(role="astrologer", text="What's my KYC status?"),
        HistoryTurn(role="assistant", text="Your KYC is pending review."),
    ]

    run_chat_turn(
        fake_client, ctx, "No I am not satisfied, connect me to a person", history=history
    )

    sent_contents = fake_client.calls[0]["contents"]
    assert len(sent_contents) == 3
    assert sent_contents[0].role == "user"
    assert sent_contents[0].parts[0].text == "What's my KYC status?"
    assert sent_contents[1].role == "model"
    assert sent_contents[1].parts[0].text == "Your KYC is pending review."
    assert sent_contents[2].role == "user"
    assert sent_contents[2].parts[0].text == "No I am not satisfied, connect me to a person"


def test_orchestrator_calls_matching_tool_and_returns_final_reply(db_session):
    ctx = make_ctx(db_session)
    fake_client = FakeAgentClient(
        [
            tool_call_response("get_kyc_status"),
            text_response("Your KYC is pending review."),
        ]
    )

    result = run_chat_turn(fake_client, ctx, "What's my KYC status?")

    assert result.reply == "Your KYC is pending review."
    assert len(result.trace) == 1
    assert result.trace[0].tool == "get_kyc_status"
    assert result.trace[0].ok is True


def _malformed_function_call_response() -> types.GenerateContentResponse:
    # Confirmed live 2026-08-18 on Vertex AI: the model tried to call a
    # tool with arguments that failed schema validation, and the response
    # came back as finish_reason=MALFORMED_FUNCTION_CALL with
    # content.parts=None — no function call, no text, nothing. Without a
    # finish_reason check, that reads as "no function call, so use the
    # (empty) text" and silently returns a blank reply with an empty trace,
    # no error at all.
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(parts=None, role=None),
                finish_reason=types.FinishReason.MALFORMED_FUNCTION_CALL,
            )
        ]
    )


def test_malformed_function_call_returns_an_apology_after_exhausting_retries(db_session):
    ctx = make_ctx(db_session)
    # One per attempt, all of them malformed — referencing the real
    # constant rather than a hardcoded number so this can't silently drift
    # out of sync with it again.
    attempts = orchestrator._MAX_GENERATE_ATTEMPTS
    fake_client = FakeAgentClient([_malformed_function_call_response() for _ in range(attempts)])

    result = run_chat_turn(fake_client, ctx, "Raise the issue to customer support")

    assert result.reply != ""
    assert result.trace == []
    assert len(fake_client.calls) == attempts


def test_malformed_function_call_recovers_transparently_on_retry(db_session):
    # Confirmed live 2026-08-18: this finish_reason is non-deterministic
    # sampling variance, not a permanent failure — retrying the identical
    # request often succeeds. The automatic retry should surface that
    # successful result, not the first attempt's failure.
    ctx = make_ctx(db_session)
    fake_client = FakeAgentClient(
        [_malformed_function_call_response(), text_response("All sorted now.")]
    )

    result = run_chat_turn(fake_client, ctx, "Raise the issue to customer support")

    assert result.reply == "All sorted now."
    assert len(fake_client.calls) == 2


def test_astrologer_id_supplied_by_the_model_is_ignored_and_overwritten(db_session, monkeypatch):
    captured = {}

    def fake_get_payout_status(db, astrologer_id):
        captured["astrologer_id"] = astrologer_id
        return payout_client.PayoutStatus(
            astrologer_id=astrologer_id,
            status="scheduled",
            amount_inr=1000,
            scheduled_date="2026-09-01",
            last_paid_date="2026-08-01",
        )

    monkeypatch.setattr(payout_client, "get_payout_status", fake_get_payout_status)

    ctx = make_ctx(db_session, astrologer_id=42)
    # A malicious/incorrect astrologer_id in the tool input must never reach the handler.
    executor.execute("get_payout_status", {"astrologer_id": 99999}, ctx)

    assert captured["astrologer_id"] == 42


def test_no_record_this_cycle_renders_an_honest_message_not_a_fabricated_breakdown(
    db_session, monkeypatch
):
    # Confirmed live 2026-08-19: a real, ops-linked astrologer missing from
    # the latest synced payout cycle used to get a confident but fabricated
    # amount/date breakdown instead of this. The tool result the model sees
    # must never contain amount_inr/last_paid_date framing for this case.
    def fake_get_payout_status(db, astrologer_id):
        return payout_client.PayoutStatus(
            astrologer_id=astrologer_id,
            status="no_record_this_cycle",
            amount_inr=0,
            scheduled_date="2026-08-28",
            last_paid_date="no record found for this astrologer in the most recently synced cycle",
        )

    monkeypatch.setattr(payout_client, "get_payout_status", fake_get_payout_status)

    ctx = make_ctx(db_session)
    result = executor.execute("get_payout_status", {}, ctx)

    assert "no_payout_record_found_for_most_recent_cycle=true" in result.content_for_model
    assert "next_payout_cycle: date=2026-08-28" in result.content_for_model
    assert "amount_inr" not in result.content_for_model
    assert "most_recently_processed_payout" not in result.content_for_model


def test_unknown_tool_returns_error_without_raising(db_session):
    ctx = make_ctx(db_session)
    result = executor.execute("delete_everything", {}, ctx)
    assert result.is_error is True


def test_create_support_ticket_reuses_attachment_shared_earlier_in_chat(
    db_session, seeded_astrologer
):
    # Regression: the astrologer shouldn't have to resend a photo/video just
    # because the model didn't repeat its exact URL when raising a ticket.
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id,
        name="Test",
        language="English",
        db=db_session,
        last_attachment_url="https://x.example/screenshot.png",
    )

    result = executor.execute(
        "create_support_ticket",
        {
            "category": "technical",
            "sub_category": "app_crash",
            "description": "App crashes on login.",
            "description_en": "App crashes on login.",
        },
        ctx,
    )

    assert result.is_error is False
    assert "https://x.example/screenshot.png" in result.content_for_model
    # Raising a ticket closes out this chat thread client-side too, same as
    # mark_issue_resolved — both are terminal actions for the conversation.
    assert result.metadata["show_feedback"] is True


def test_non_vip_technical_ticket_requires_evidence(db_session, seeded_astrologer, monkeypatch):
    _force_priority(monkeypatch, priority=3)
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id, name="Test", language="English", db=db_session
    )

    result = executor.execute(
        "create_support_ticket",
        {
            "category": "technical",
            "sub_category": "app_crash",
            "description": "App crashes on login.",
            "description_en": "App crashes on login.",
        },
        ctx,
    )

    assert result.is_error is True


def test_non_vip_technical_ticket_succeeds_with_evidence(
    db_session, seeded_astrologer, monkeypatch
):
    _force_priority(monkeypatch, priority=3)
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id,
        name="Test",
        language="English",
        db=db_session,
        last_attachment_url="https://x.example/screenshot.png",
    )

    result = executor.execute(
        "create_support_ticket",
        {
            "category": "technical",
            "sub_category": "app_crash",
            "description": "App crashes on login.",
            "description_en": "App crashes on login.",
        },
        ctx,
    )

    assert result.is_error is False


def test_vip_technical_ticket_also_requires_evidence(db_session, seeded_astrologer, monkeypatch):
    # 2026-08-13 policy update: evidence is required at every priority level
    # now — priority only changes whether the bot analyzes/troubleshoots
    # with it, not whether it's needed at all.
    _force_priority(monkeypatch, priority=1)
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id, name="Test", language="English", db=db_session
    )

    result = executor.execute(
        "create_support_ticket",
        {
            "category": "technical",
            "sub_category": "app_crash",
            "description": "App crashes on login.",
            "description_en": "App crashes on login.",
        },
        ctx,
    )

    assert result.is_error is True


def test_vip_technical_ticket_succeeds_with_evidence(db_session, seeded_astrologer, monkeypatch):
    _force_priority(monkeypatch, priority=1)
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id,
        name="Test",
        language="English",
        db=db_session,
        last_attachment_url="https://x.example/screenshot.png",
    )

    result = executor.execute(
        "create_support_ticket",
        {
            "category": "technical",
            "sub_category": "app_crash",
            "description": "App crashes on login.",
            "description_en": "App crashes on login.",
        },
        ctx,
    )

    assert result.is_error is False


def test_create_support_ticket_refuses_a_duplicate_for_an_open_ticket(
    db_session, seeded_astrologer
):
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id, name="Test", language="English", db=db_session
    )
    first = executor.execute(
        "create_support_ticket",
        {
            "category": "technical",
            "sub_category": "app_crash",
            "description": "App crashes on login.",
            "description_en": "App crashes on login.",
            "attachment_url": "https://x.example/screenshot.png",
        },
        ctx,
    )
    assert first.is_error is False

    second = executor.execute(
        "create_support_ticket",
        {
            "category": "technical",
            "sub_category": "app_crash",
            "description": "Still crashing.",
            "description_en": "Still crashing.",
            "attachment_url": "https://x.example/screenshot2.png",
        },
        ctx,
    )

    assert second.is_error is True
    assert "already" in second.content_for_model.lower()


def test_create_support_ticket_allows_a_new_ticket_after_the_first_resolves(
    db_session, seeded_astrologer
):
    from app.models.enums import TicketStatus
    from app.services import ticket_service

    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id, name="Test", language="English", db=db_session
    )
    first = executor.execute(
        "create_support_ticket",
        {
            "category": "technical",
            "sub_category": "app_crash",
            "description": "App crashes on login.",
            "description_en": "App crashes on login.",
            "attachment_url": "https://x.example/screenshot.png",
        },
        ctx,
    )
    ticket = ticket_service.get_ticket(db_session, first.metadata["created_ticket_id"])
    ticket_service.transition_status(
        db_session, ticket, TicketStatus.RESOLVED, changed_by="admin@test.example", note="Fixed"
    )
    # CLOSED is no longer manually settable — reach it the real way, via
    # the astrologer confirming it's fixed.
    ticket_service.record_satisfaction(db_session, ticket, satisfied=True)

    second = executor.execute(
        "create_support_ticket",
        {
            "category": "technical",
            "sub_category": "app_crash",
            "description": "Crashing again, a new issue.",
            "description_en": "Crashing again, a new issue.",
            "attachment_url": "https://x.example/screenshot2.png",
        },
        ctx,
    )

    assert second.is_error is False


def test_create_support_ticket_names_the_kam_when_actually_notified(
    db_session, seeded_astrologer, monkeypatch
):
    # "profile" (photo change) always routes direct-to-KAM regardless of
    # priority — the model should get the real KAM name back, not just an id.
    _force_priority(monkeypatch, priority=5)
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id,
        name="Test",
        language="English",
        db=db_session,
        last_attachment_url="https://x.example/photo.png",
    )

    result = executor.execute(
        "create_support_ticket",
        {
            "category": "profile",
            "sub_category": "photo_change",
            "description": "Wants a new profile photo.",
            "description_en": "Wants a new profile photo.",
        },
        ctx,
    )

    assert result.is_error is False
    assert "notified_kam_name=Test Admin" in result.content_for_model


def test_create_support_ticket_names_no_one_for_a_standard_non_vip_ticket(
    db_session, seeded_astrologer, monkeypatch
):
    # Non-VIP + a category with no direct-to-KAM carve-out: the astrologer's
    # personal KAM is still nominally assigned but was never actually paged,
    # so the model must not be told a specific name (would overclaim).
    _force_priority(monkeypatch, priority=5)
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id,
        name="Test",
        language="English",
        db=db_session,
        last_attachment_url="https://x.example/screenshot.png",
    )

    result = executor.execute(
        "create_support_ticket",
        {
            "category": "technical",
            "sub_category": "app_crash",
            "description": "App crashes on login.",
            "description_en": "App crashes on login.",
        },
        ctx,
    )

    assert result.is_error is False
    assert "notified_kam_name=None" in result.content_for_model


def test_get_assigned_admin_returns_the_real_name_not_just_an_id(db_session, seeded_astrologer):
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id, name="Test", language="English", db=db_session
    )

    result = executor.execute("get_assigned_admin", {}, ctx)

    assert result.content_for_model == "assigned_admin_name=Test Admin"


def test_non_vip_no_visibility_ticket_requires_a_prior_reply_first(
    db_session, seeded_astrologer, monkeypatch
):
    # Code-enforced gate (2026-08-16): a non-VIP astrologer's very first
    # message about low calls can't skip straight to a ticket, regardless of
    # what the model decides — see tool_registry._handle_create_support_ticket.
    _force_priority(monkeypatch, priority=5)
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id, name="Test", language="English", db=db_session
    )

    result = executor.execute(
        "create_support_ticket",
        {
            "category": "no_visibility",
            "sub_category": "low_visibility",
            "description": "Not getting enough calls.",
            "description_en": "Not getting enough calls.",
        },
        ctx,
    )

    assert result.is_error is True


def test_non_vip_no_visibility_ticket_succeeds_after_a_prior_reply(
    db_session, seeded_astrologer, monkeypatch
):
    _force_priority(monkeypatch, priority=5)
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id,
        name="Test",
        language="English",
        db=db_session,
        has_prior_reply=True,
    )

    result = executor.execute(
        "create_support_ticket",
        {
            "category": "no_visibility",
            "sub_category": "low_visibility",
            "description": "Still not getting enough calls after trying the advice.",
            "description_en": "Still not getting enough calls after trying the advice.",
        },
        ctx,
    )

    assert result.is_error is False


def test_vip_no_visibility_ticket_succeeds_on_the_first_message(
    db_session, seeded_astrologer, monkeypatch
):
    # VIP (P1/P2) skips the self-help gate entirely — escalate immediately.
    _force_priority(monkeypatch, priority=1)
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id, name="Test", language="English", db=db_session
    )

    result = executor.execute(
        "create_support_ticket",
        {
            "category": "no_visibility",
            "sub_category": "low_visibility",
            "description": "Not getting enough calls.",
            "description_en": "Not getting enough calls.",
        },
        ctx,
    )

    assert result.is_error is False


def test_analyze_screenshot_without_any_image_errors_cleanly(db_session):
    ctx = make_ctx(db_session)
    result = executor.execute("analyze_screenshot", {"question": "what's wrong?"}, ctx)
    assert result.is_error is True


def test_mark_issue_resolved_flags_show_feedback(db_session, seeded_astrologer):
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id,
        name="Test",
        language="English",
        db=db_session,
        session_id="sess-feedback",
    )

    result = executor.execute(
        "mark_issue_resolved", {"category": "technical", "sub_category": "app_crash"}, ctx
    )

    assert result.is_error is False
    assert result.metadata == {"show_feedback": True}


def test_orchestrator_surfaces_tool_metadata_on_the_turn_result(db_session, seeded_astrologer):
    ctx = SessionContext(
        astrologer_id=seeded_astrologer.id,
        name="Test",
        language="English",
        db=db_session,
        session_id="sess-feedback-2",
    )
    fake_client = FakeAgentClient(
        [
            tool_call_response(
                "mark_issue_resolved", {"category": "technical", "sub_category": "app_crash"}
            ),
            text_response("Glad that helped!"),
        ]
    )

    result = run_chat_turn(fake_client, ctx, "Yes that fixed it")

    assert result.reply == "Glad that helped!"
    assert result.metadata == {"show_feedback": True}


def test_orchestrator_stops_at_max_iterations(db_session):
    ctx = make_ctx(db_session)
    # Never returns a plain text-only turn — the loop must not run forever.
    endless_tool_call = tool_call_response("get_tickets")
    fake_client = FakeAgentClient([endless_tool_call] * (MAX_ITERATIONS + 5))

    result = run_chat_turn(fake_client, ctx, "loop forever")

    assert len(fake_client.calls) == MAX_ITERATIONS
    assert len(result.trace) == MAX_ITERATIONS


def test_get_salary_details_is_not_offered_to_the_model():
    # salary_client.py is 100% mocked with no real data source at all (no
    # sheet, no seed data) — confirmed live 2026-08-18: it told a real
    # astrologer a specific fabricated salary figure and revision date with
    # full confidence. Must never be something the model can call until (if
    # ever) a real salary integration exists.
    assert "get_salary_details" not in {tool["name"] for tool in tool_schemas.ALL_TOOLS}
    assert "get_salary_details" not in REGISTRY
