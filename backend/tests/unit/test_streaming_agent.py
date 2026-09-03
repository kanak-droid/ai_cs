from app.agent.client import StreamDelta, StreamToolCallDelta
from app.agent.orchestrator import run_streaming_chat_turn
from app.integrations import payout_client
from tests.unit.test_agent_tool_selection import make_ctx


class FakeStreamingAgentClient:
    """Returns predefined SSE-like chunks without contacting OpenRouter."""

    def __init__(self, responses: list[list[StreamDelta]]):
        self.responses = list(responses)

    def generate(self, *, system, contents, tools):
        raise AssertionError("Streaming client should not use generate()")

    def stream_generate(self, *, system, contents, tools):
        yield from self.responses.pop(0)


def test_streaming_agent_forwards_text_chunks_as_soon_as_they_arrive(db_session):
    client = FakeStreamingAgentClient(
        [[StreamDelta(text="Your payout "), StreamDelta(text="is scheduled.")]]
    )
    received = []

    result = run_streaming_chat_turn(
        client,
        make_ctx(db_session),
        "When is my payout?",
        on_text=received.append,
    )

    assert received == ["Your payout ", "is scheduled."]
    assert result.reply == "Your payout is scheduled."
    assert result.trace == []


def test_streaming_agent_executes_tools_before_streaming_the_final_answer(db_session, monkeypatch):
    def fake_get_payout_status(db, astrologer_id):
        return payout_client.PayoutStatus(
            astrologer_id=astrologer_id,
            status="scheduled",
            amount_inr=1000,
            scheduled_date="2026-09-05",
            last_paid_date="2026-08-05",
        )

    monkeypatch.setattr(payout_client, "get_payout_status", fake_get_payout_status)
    client = FakeStreamingAgentClient(
        [
            [
                StreamDelta(
                    tool_calls=(
                        StreamToolCallDelta(index=0, name="get_payout_status", arguments="{}"),
                    )
                )
            ],
            [StreamDelta(text="Your payout is scheduled for September fifth.")],
        ]
    )
    received = []

    result = run_streaming_chat_turn(
        client,
        make_ctx(db_session),
        "When is my payout?",
        on_text=received.append,
    )

    assert received == ["Your payout is scheduled for September fifth."]
    assert result.reply == "Your payout is scheduled for September fifth."
    assert [step.tool for step in result.trace] == ["get_payout_status"]
