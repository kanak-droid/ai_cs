"""The Claude tool-calling loop for one chat turn.

Hand-written (not the Anthropic beta Tool Runner) so the astrologer_id
enforcement in agent/executor.py and the trace-building below both sit
explicitly between "Claude asked for a tool" and "the tool actually ran" —
a boundary worth keeping visible and reviewable rather than hidden inside a
generic runner's hook API.

This module imports ONLY app.agent.tool_schemas (pure data) plus
app.agent.executor for dispatch — never app.services or app.integrations
directly.
"""

from dataclasses import dataclass

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


def _content_block_to_dict(block) -> dict:
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    raise ValueError(f"Unsupported content block type: {block.type}")


def run_chat_turn(client: AgentClient, ctx: SessionContext, user_message: str) -> ChatTurnResult:
    system = render_system_prompt(name=ctx.name, language=ctx.language)
    messages: list[dict] = [{"role": "user", "content": user_message}]
    trace = AgentTrace()

    for _ in range(MAX_ITERATIONS):
        response = client.create(system=system, messages=messages, tools=tool_schemas.ALL_TOOLS)
        messages.append(
            {"role": "assistant", "content": [_content_block_to_dict(b) for b in response.content]}
        )

        if response.stop_reason != "tool_use":
            final_text = "".join(b.text for b in response.content if b.type == "text")
            return ChatTurnResult(reply=final_text, trace=trace.to_list())

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        tool_results = []
        for block in tool_use_blocks:
            result = executor.execute(block.name, block.input, ctx)
            trace.add(tool=block.name, ok=not result.is_error, summary=result.summary_for_trace)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result.content_for_claude,
                    "is_error": result.is_error,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    trace.truncated = True
    return ChatTurnResult(
        reply="I've had to pause here — could you try rephrasing your question?",
        trace=trace.to_list(),
    )
