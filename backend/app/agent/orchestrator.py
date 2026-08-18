"""The Gemini tool-calling loop for one chat turn.

Hand-written (rather than an auto-continuing helper) so the astrologer_id
enforcement in agent/executor.py and the trace-building below both sit
explicitly between "the model asked for a tool" and "the tool actually ran" —
a boundary worth keeping visible and reviewable rather than hidden inside a
generic runner's hook API.

This module imports app.agent.tool_schemas (pure data) plus app.agent.executor
for dispatch — never app.services or app.integrations directly. It does talk
directly to the google.genai `types` module, which is the AI provider's wire
format, not a business-logic dependency.
"""

import logging
from dataclasses import dataclass, field

from google.genai import types

from app.agent import executor, tool_schemas
from app.agent.client import AgentClient
from app.agent.context import SessionContext
from app.agent.prompt import render_system_prompt
from app.agent.trace import AgentTrace, AgentTraceStep

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 8
_APOLOGY_REPLY = "Sorry, I couldn't process that — could you try again?"
# Confirmed live 2026-08-18 on Vertex AI: a candidate with a non-STOP
# finish_reason (MALFORMED_FUNCTION_CALL — a tool call with arguments that
# failed schema validation — and also observed UNEXPECTED_TOOL_CALL) is
# non-deterministic sampling variance, not a permanent failure. A broad
# smoke test across many real conversations found this landed on ~16% of
# turns even after 3 attempts each, so retrying resolves most but not all
# of these. Bumped 5 -> 7 (2026-08-18) after live testing of the
# create_support_ticket flow specifically: it has more/longer arguments
# (category, sub_category, description, description_en, attachment_url)
# than most other tools, and hit exhausted-retry apologies noticeably more
# often than simple lookups in that same test batch — worth a wider budget
# on the one call this whole ticket-raising fix depends on landing.
_MAX_GENERATE_ATTEMPTS = 7


def _is_usable(response: types.GenerateContentResponse) -> bool:
    if not response.candidates or response.candidates[0].content is None:
        return False
    return response.candidates[0].finish_reason in (None, types.FinishReason.STOP)


def _generate_with_retry(
    client: AgentClient, *, system: str, contents: list[types.Content], tools: list[types.Tool]
) -> types.GenerateContentResponse:
    response = client.generate(system=system, contents=contents, tools=tools)
    for attempt in range(1, _MAX_GENERATE_ATTEMPTS):
        if _is_usable(response):
            return response
        logger.warning(
            "Gemini response unusable (finish_reason=%s) on attempt %d/%d — retrying",
            response.candidates[0].finish_reason if response.candidates else None,
            attempt,
            _MAX_GENERATE_ATTEMPTS,
        )
        response = client.generate(system=system, contents=contents, tools=tools)
    return response


@dataclass(frozen=True)
class ChatTurnResult:
    reply: str
    trace: list[AgentTraceStep]
    # Merged from every tool call's ToolResult.metadata this turn (last write
    # wins on key collision) — e.g. created_ticket_id, show_feedback. Never
    # seen by the model; chat_service/routes map this onto ChatResponse.
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class HistoryTurn:
    """One earlier turn of this conversation, supplied by the caller.

    The backend is stateless across /api/chat requests, so without this the
    model has no memory of anything said before the current message — which
    among other things makes it impossible for it to write a ticket summary
    that reflects the real issue rather than just the astrologer's latest
    message.
    """

    role: str  # "astrologer" | "assistant"
    text: str


def _build_tools() -> list[types.Tool]:
    return [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters_json_schema=tool["input_schema"],
                )
                for tool in tool_schemas.ALL_TOOLS
            ]
        )
    ]


def run_chat_turn(
    client: AgentClient,
    ctx: SessionContext,
    user_message: str,
    *,
    history: list[HistoryTurn] | None = None,
) -> ChatTurnResult:
    system = render_system_prompt(name=ctx.name, language=ctx.language)
    tools = _build_tools()
    contents: list[types.Content] = [
        types.Content(
            role="user" if turn.role == "astrologer" else "model",
            parts=[types.Part(text=turn.text)],
        )
        for turn in (history or [])
    ]
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))
    trace = AgentTrace()
    metadata: dict = {}

    for _ in range(MAX_ITERATIONS):
        response = _generate_with_retry(client, system=system, contents=contents, tools=tools)

        # Still unusable after retrying — a non-STOP finish_reason (e.g.
        # MALFORMED_FUNCTION_CALL) means this candidate has to be treated
        # as unusable even though it technically exists (content.parts is
        # None in that case). Without this check, that would silently read
        # as "no function call, so use the text" below — parts is empty,
        # so the "text" is "" — and return a blank reply with an empty
        # trace, no error at all, instead of surfacing the failure.
        if not _is_usable(response):
            logger.warning(
                "Gemini response still unusable after %d attempts (finish_reason=%s) — "
                "returning apology instead of a possibly-empty reply",
                _MAX_GENERATE_ATTEMPTS,
                response.candidates[0].finish_reason if response.candidates else None,
            )
            return ChatTurnResult(reply=_APOLOGY_REPLY, trace=trace.to_list(), metadata=metadata)

        model_content = response.candidates[0].content
        contents.append(model_content)
        parts = model_content.parts or []

        function_call_parts = [p for p in parts if p.function_call is not None]
        if not function_call_parts:
            final_text = "".join(p.text for p in parts if p.text is not None)
            return ChatTurnResult(reply=final_text, trace=trace.to_list(), metadata=metadata)

        response_parts = []
        for part in function_call_parts:
            call = part.function_call
            result = executor.execute(call.name, dict(call.args or {}), ctx)
            trace.add(tool=call.name, ok=not result.is_error, summary=result.summary_for_trace)
            metadata.update(result.metadata)
            response_parts.append(
                types.Part.from_function_response(
                    name=call.name, response={"result": result.content_for_model}
                )
            )
        # The live API rejects role="tool" ("Role 'tool' is not supported") despite
        # some Gemini docs suggesting otherwise — function responses go back as a
        # "user" turn, verified against the real API before landing this.
        contents.append(types.Content(role="user", parts=response_parts))

    trace.truncated = True
    return ChatTurnResult(
        reply="I've had to pause here — could you try rephrasing your question?",
        trace=trace.to_list(),
        metadata=metadata,
    )
