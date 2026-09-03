import json

import httpx
from google.genai import types

from app.agent import orchestrator
from app.agent.openrouter_client import (
    OpenRouterAgentClient,
    _contents_to_messages,
    _parse_response,
    _tools_to_openai,
)
from app.agent.orchestrator import run_chat_turn
from app.core.config import settings
from tests.unit.test_agent_tool_selection import make_ctx


def test_tools_to_openai_flattens_function_declarations():
    tools = orchestrator._build_tools()
    openai_tools = _tools_to_openai(tools)
    names = {t["function"]["name"] for t in openai_tools}
    assert "get_payout_status" in names
    payout_tool = next(t for t in openai_tools if t["function"]["name"] == "get_payout_status")
    assert payout_tool["type"] == "function"
    assert payout_tool["function"]["parameters"] == {"type": "object", "properties": {}}


def test_contents_to_messages_maps_plain_history():
    contents = [
        types.Content(role="user", parts=[types.Part(text="What's my KYC status?")]),
        types.Content(role="model", parts=[types.Part(text="Your KYC is pending review.")]),
        types.Content(role="user", parts=[types.Part(text="Ok thanks")]),
    ]
    messages = _contents_to_messages("system prompt", contents)
    assert messages == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "What's my KYC status?"},
        {"role": "assistant", "content": "Your KYC is pending review."},
        {"role": "user", "content": "Ok thanks"},
    ]


def test_contents_to_messages_pairs_tool_call_and_response_by_position():
    # Mirrors exactly what orchestrator.run_chat_turn appends to `contents`
    # for one function-call round trip.
    contents = [
        types.Content(role="user", parts=[types.Part(text="What's my payout?")]),
        types.Content(
            role="model",
            parts=[types.Part(function_call=types.FunctionCall(name="get_payout_status", args={}))],
        ),
        types.Content(
            role="user",
            parts=[
                types.Part.from_function_response(
                    name="get_payout_status", response={"result": "amount_inr=500"}
                )
            ],
        ),
    ]
    messages = _contents_to_messages("sys", contents)

    assistant_msg = messages[2]
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["tool_calls"][0]["function"]["name"] == "get_payout_status"
    tool_call_id = assistant_msg["tool_calls"][0]["id"]

    tool_msg = messages[3]
    assert tool_msg == {"role": "tool", "tool_call_id": tool_call_id, "content": "amount_inr=500"}


def test_parse_response_extracts_text():
    body = {"choices": [{"message": {"role": "assistant", "content": "Hello there"}}]}
    response = _parse_response(body)
    assert response.candidates[0].finish_reason == types.FinishReason.STOP
    assert response.candidates[0].content.parts[0].text == "Hello there"


def test_parse_response_extracts_tool_calls():
    body = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "type": "function",
                            "function": {"name": "get_payout_status", "arguments": "{}"},
                        }
                    ],
                }
            }
        ]
    }
    response = _parse_response(body)
    call = response.candidates[0].content.parts[0].function_call
    assert call.name == "get_payout_status"
    assert dict(call.args or {}) == {}


def _openai_text_response(text: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


def _openai_tool_call_response(name: str, args: dict | None = None) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(args or {})},
                        }
                    ],
                }
            }
        ]
    }


class _FakeHttpResponse:
    def __init__(self, body: dict):
        self._body = body

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._body


class _FakeStreamResponse:
    """Context-managed SSE response used to test OpenRouter chunk parsing."""

    def __init__(self, lines: list[str]):
        self._lines = lines

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def raise_for_status(self) -> None:
        pass

    def iter_lines(self):
        yield from self._lines


def test_openrouter_client_parses_text_and_tool_sse_chunks(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")
    lines = [
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"get_payout_status","arguments":"{}"}}]}}]}',
        'data: {"choices":[{"delta":{"content":"Your payout is "}}]}',
        'data: {"choices":[{"delta":{"content":"scheduled."}}]}',
        "data: [DONE]",
    ]

    def fake_stream(method, url, **kwargs):
        assert method == "POST"
        assert url == "https://openrouter.ai/api/v1/chat/completions"
        assert kwargs["json"]["stream"] is True
        return _FakeStreamResponse(lines)

    monkeypatch.setattr(httpx, "stream", fake_stream)
    chunks = list(
        OpenRouterAgentClient().stream_generate(
            system="system",
            contents=[types.Content(role="user", parts=[types.Part(text="hello")])],
            tools=[],
        )
    )

    assert chunks[0].tool_calls[0].name == "get_payout_status"
    assert chunks[0].tool_calls[0].arguments == "{}"
    assert [chunk.text for chunk in chunks[1:]] == ["Your payout is ", "scheduled."]


def test_openrouter_client_end_to_end_through_orchestrator(db_session, monkeypatch):
    """The real OpenRouterAgentClient, wired into the real orchestrator loop
    and the real executor/tool_registry — only the network call is faked,
    so this proves the whole translation layer (not just isolated
    functions) actually round-trips a tool call the way Gemini's does.
    """
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")

    responses = [
        _openai_tool_call_response("get_payout_status"),
        _openai_text_response("Your payout is scheduled for the 5th."),
    ]

    def fake_post(url, **kwargs):
        assert url == "https://openrouter.ai/api/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"
        return _FakeHttpResponse(responses.pop(0))

    monkeypatch.setattr(httpx, "post", fake_post)

    ctx = make_ctx(db_session)
    result = run_chat_turn(OpenRouterAgentClient(), ctx, "When is my payout?")

    assert result.reply == "Your payout is scheduled for the 5th."
    assert [step.tool for step in result.trace] == ["get_payout_status"]
    assert result.trace[0].ok is True
