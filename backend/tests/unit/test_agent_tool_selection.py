from app.agent import executor
from app.agent.context import SessionContext
from app.agent.orchestrator import MAX_ITERATIONS, run_chat_turn
from app.integrations import payout_client


class FakeBlock:
    def __init__(self, type, **kwargs):
        self.type = type
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeMessage:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class FakeAgentClient:
    """Constructor-injected fake — never touches the real Anthropic API."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, *, system, messages, tools):
        self.calls.append({"system": system, "messages": messages, "tools": tools})
        return self.responses.pop(0)


def make_ctx(db_session, astrologer_id=1) -> SessionContext:
    return SessionContext(astrologer_id=astrologer_id, name="Test", language="English", db=db_session)


def test_orchestrator_calls_matching_tool_and_returns_final_reply(db_session):
    ctx = make_ctx(db_session)
    fake_client = FakeAgentClient(
        [
            FakeMessage(
                content=[
                    FakeBlock("tool_use", id="tool_1", name="get_kyc_status", input={})
                ],
                stop_reason="tool_use",
            ),
            FakeMessage(
                content=[FakeBlock("text", text="Your KYC is pending review.")],
                stop_reason="end_turn",
            ),
        ]
    )

    result = run_chat_turn(fake_client, ctx, "What's my KYC status?")

    assert result.reply == "Your KYC is pending review."
    assert len(result.trace) == 1
    assert result.trace[0].tool == "get_kyc_status"
    assert result.trace[0].ok is True


def test_astrologer_id_supplied_by_claude_is_ignored_and_overwritten(db_session, monkeypatch):
    captured = {}

    def fake_get_payout_status(astrologer_id):
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


def test_unknown_tool_returns_error_without_raising(db_session):
    ctx = make_ctx(db_session)
    result = executor.execute("delete_everything", {}, ctx)
    assert result.is_error is True


def test_orchestrator_stops_at_max_iterations(db_session):
    ctx = make_ctx(db_session)
    # Never returns end_turn — the loop must not run forever.
    endless_tool_use = FakeMessage(
        content=[FakeBlock("tool_use", id="tool_x", name="get_tickets", input={})],
        stop_reason="tool_use",
    )
    fake_client = FakeAgentClient([endless_tool_use] * (MAX_ITERATIONS + 5))

    result = run_chat_turn(fake_client, ctx, "loop forever")

    assert len(fake_client.calls) == MAX_ITERATIONS
    assert len(result.trace) == MAX_ITERATIONS
