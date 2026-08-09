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

from dataclasses import dataclass

from google.genai import types

from app.agent import executor, tool_schemas
from app.agent.client import AgentClient
from app.agent.context import SessionContext
from app.agent.prompt import render_system_prompt
from app.agent.trace import AgentTrace, AgentTraceStep

MAX_ITERATIONS = 8


@dataclass(frozen=True)
class ChatTurnResult:
    reply: str
    trace: list[AgentTraceStep]


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


def run_chat_turn(client: AgentClient, ctx: SessionContext, user_message: str) -> ChatTurnResult:
    system = render_system_prompt(name=ctx.name, language=ctx.language)
    tools = _build_tools()
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=user_message)])
    ]
    trace = AgentTrace()

    for _ in range(MAX_ITERATIONS):
        response = client.generate(system=system, contents=contents, tools=tools)

        if not response.candidates or response.candidates[0].content is None:
            return ChatTurnResult(
                reply="Sorry, I couldn't process that — could you try again?",
                trace=trace.to_list(),
            )

        model_content = response.candidates[0].content
        contents.append(model_content)
        parts = model_content.parts or []

        function_call_parts = [p for p in parts if p.function_call is not None]
        if not function_call_parts:
            final_text = "".join(p.text for p in parts if p.text is not None)
            return ChatTurnResult(reply=final_text, trace=trace.to_list())

        response_parts = []
        for part in function_call_parts:
            call = part.function_call
            result = executor.execute(call.name, dict(call.args or {}), ctx)
            trace.add(tool=call.name, ok=not result.is_error, summary=result.summary_for_trace)
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
    )
