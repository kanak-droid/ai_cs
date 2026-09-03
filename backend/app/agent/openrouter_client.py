"""OpenAI-compatible AgentClient backed by OpenRouter (https://openrouter.ai)
— implements the exact same Protocol as GeminiAgentClient (see client.py), so
orchestrator.run_chat_turn's tool-calling loop works identically regardless
of which one is plugged in. Used for the AI phone call (see call_service.py,
get_voice_agent_client below) — text chat stays on Gemini by default; the two
agents can run on entirely different model providers since only the
tool-calling loop and tool_registry.py are actually shared between them.

orchestrator.py builds/reads Gemini's `types.Content`/`types.Part` wire
format directly, including two Gemini-specific quirks this client has to
translate around:

  1. A tool call from the model is a `Part(function_call=...)` inside a
     role="model" Content; the result goes back as a role="user" Content of
     `Part(function_response=...)` right after — Gemini's live API rejects
     role="tool" outright (see orchestrator.py's comment), unlike OpenAI's
     format, which uses a dedicated "tool" role keyed by a tool_call id.
     Gemini's format has no such id, so this client invents one purely from
     each part's position (content index, part index) — recomputed fresh on
     every call from `contents` alone, never stored on the client, since nothing
     else in this call chain gives it anywhere durable to keep it.
  2. `_is_usable` (orchestrator.py) only treats finish_reason None/STOP as
     usable — that check exists for Gemini-specific failure reasons
     (MALFORMED_FUNCTION_CALL etc.) that don't apply here, so this client
     reports STOP for any well-formed response and only something else when
     the response is genuinely empty, to still get the orchestrator's
     existing retry-on-bad-response behavior for free.
"""

import json
import logging
from collections.abc import Iterator

import httpx
from google.genai import types

from app.agent.client import StreamDelta, StreamToolCallDelta
from app.core.config import settings

logger = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_REQUEST_TIMEOUT_SECONDS = 30.0
_STREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
_MAX_OUTPUT_TOKENS = 2048


def _provider_config() -> dict:
    """Returns optional provider routing shared by all OpenRouter requests."""
    if not settings.OPENROUTER_PROVIDER_ORDER:
        return {}
    return {"provider": {"order": settings.OPENROUTER_PROVIDER_ORDER.split(",")}}


def _headers() -> dict[str, str]:
    """Builds the standard authenticated OpenRouter request headers."""
    return {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }


def _tools_to_openai(tools: list[types.Tool]) -> list[dict]:
    openai_tools = []
    for tool in tools:
        for fd in tool.function_declarations or []:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": fd.name,
                        "description": fd.description,
                        "parameters": fd.parameters_json_schema,
                    },
                }
            )
    return openai_tools


def _contents_to_messages(system: str, contents: list[types.Content]) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": system}]
    # Set right after emitting an assistant tool-calls message, consumed by
    # the function-response content that (per orchestrator.py) always comes
    # immediately after it — pairs each result back to the call it answers.
    pending_call_ids: list[str] | None = None

    for i, content in enumerate(contents):
        parts = content.parts or []
        function_calls = [p.function_call for p in parts if p.function_call is not None]
        function_responses = [p.function_response for p in parts if p.function_response is not None]

        if function_calls:
            call_ids = [f"call_{i}_{j}" for j in range(len(function_calls))]
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(dict(call.args or {})),
                            },
                        }
                        for call_id, call in zip(call_ids, function_calls)
                    ],
                }
            )
            pending_call_ids = call_ids
            continue

        if function_responses:
            ids = pending_call_ids or [f"call_{i}_{j}" for j in range(len(function_responses))]
            for call_id, resp in zip(ids, function_responses):
                result = (resp.response or {}).get("result", "")
                messages.append({"role": "tool", "tool_call_id": call_id, "content": str(result)})
            pending_call_ids = None
            continue

        text = "".join(p.text for p in parts if p.text is not None)
        role = "assistant" if content.role == "model" else "user"
        messages.append({"role": role, "content": text})

    return messages


def _parse_response(body: dict) -> types.GenerateContentResponse:
    choices = body.get("choices") or []
    if not choices:
        logger.warning("OpenRouter response had no choices: %s", body)
        return types.GenerateContentResponse(
            candidates=[types.Candidate(content=None, finish_reason=types.FinishReason.OTHER)]
        )

    message = choices[0].get("message") or {}
    tool_calls = message.get("tool_calls") or []

    if tool_calls:
        parts = [
            types.Part(
                function_call=types.FunctionCall(
                    name=tc["function"]["name"],
                    args=json.loads(tc["function"]["arguments"] or "{}"),
                )
            )
            for tc in tool_calls
        ]
    else:
        parts = [types.Part(text=message.get("content") or "")]

    content = types.Content(role="model", parts=parts)
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=content, finish_reason=types.FinishReason.STOP)]
    )


class OpenRouterAgentClient:
    def __init__(self) -> None:
        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

    def generate(
        self, *, system: str, contents: list[types.Content], tools: list[types.Tool]
    ) -> types.GenerateContentResponse:
        body = {
            "model": settings.OPENROUTER_MODEL,
            "messages": _contents_to_messages(system, contents),
            "tools": _tools_to_openai(tools),
            "max_tokens": _MAX_OUTPUT_TOKENS,
        }
        body.update(_provider_config())

        response = httpx.post(
            _OPENROUTER_URL,
            headers=_headers(),
            json=body,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return _parse_response(response.json())

    def stream_generate(
        self, *, system: str, contents: list[types.Content], tools: list[types.Tool]
    ) -> Iterator[StreamDelta]:
        """Streams OpenRouter SSE response fragments for a voice turn."""
        body = {
            "model": settings.OPENROUTER_MODEL,
            "messages": _contents_to_messages(system, contents),
            "tools": _tools_to_openai(tools),
            "max_tokens": _MAX_OUTPUT_TOKENS,
            "stream": True,
        }
        body.update(_provider_config())

        with httpx.stream(
            "POST",
            _OPENROUTER_URL,
            headers=_headers(),
            json=body,
            timeout=_STREAM_TIMEOUT,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                payload = line.removeprefix("data: ")
                if payload == "[DONE]":
                    return
                chunk = json.loads(payload)
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                tool_calls = tuple(
                    StreamToolCallDelta(
                        index=tool_call.get("index", 0),
                        name=(tool_call.get("function") or {}).get("name"),
                        arguments=(tool_call.get("function") or {}).get("arguments"),
                    )
                    for tool_call in delta.get("tool_calls") or []
                )
                text = delta.get("content") or ""
                if text or tool_calls:
                    yield StreamDelta(text=text, tool_calls=tool_calls)

    def generate_call_summary(self, *, prompt: str) -> str:
        """Returns a compact JSON outcome summary for a completed call."""
        body = {
            "model": settings.OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You produce accurate customer-support call outcomes. "
                        "Return only valid JSON with summary, resolution_status, "
                        "suggested_solution, and next_action string fields."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
        }
        body.update(_provider_config())
        response = httpx.post(
            _OPENROUTER_URL, headers=_headers(), json=body, timeout=_REQUEST_TIMEOUT_SECONDS
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in (400, 422):
                raise
            body.pop("response_format")
            response = httpx.post(
                _OPENROUTER_URL,
                headers=_headers(),
                json=body,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        return ((response.json().get("choices") or [{}])[0].get("message") or {}).get(
            "content"
        ) or "{}"


def get_voice_agent_client() -> OpenRouterAgentClient:
    return OpenRouterAgentClient()
