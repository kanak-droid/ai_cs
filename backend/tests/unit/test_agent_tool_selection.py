from google.genai import types

from app.agent import executor
from app.agent.context import SessionContext
from app.agent.orchestrator import MAX_ITERATIONS, HistoryTurn, run_chat_turn
from app.integrations import payout_client


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


def test_astrologer_id_supplied_by_the_model_is_ignored_and_overwritten(db_session, monkeypatch):
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
    # Never returns a plain text-only turn — the loop must not run forever.
    endless_tool_call = tool_call_response("get_tickets")
    fake_client = FakeAgentClient([endless_tool_call] * (MAX_ITERATIONS + 5))

    result = run_chat_turn(fake_client, ctx, "loop forever")

    assert len(fake_client.calls) == MAX_ITERATIONS
    assert len(result.trace) == MAX_ITERATIONS
