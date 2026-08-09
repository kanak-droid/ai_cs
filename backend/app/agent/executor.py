"""The single choke point every tool call passes through.

SECURITY BOUNDARY: astrologer_id is unconditionally stripped from whatever
the model supplied and replaced with the authenticated session's real id,
before any handler (and therefore any service/integration) ever sees it.
This holds even under prompt injection — e.g. a malicious ticket description
telling the model to emit a different astrologer_id renders inert here,
because the value is never read, only overwritten.

This is also the only file in app/agent/ that imports app.services /
app.integrations (transitively, via app.agent.tool_registry) — the
orchestrator itself only ever imports app.agent.tool_schemas (pure data).
"""

import logging

from app.agent.context import SessionContext
from app.agent.tool_registry import REGISTRY, ToolResult

logger = logging.getLogger(__name__)


def execute(tool_name: str, tool_input: dict, ctx: SessionContext) -> ToolResult:
    spec = REGISTRY.get(tool_name)
    if spec is None:
        return ToolResult(
            content_for_model=f"error: unknown tool '{tool_name}'",
            summary_for_trace=f"Tried to call unknown tool '{tool_name}'",
            is_error=True,
        )

    safe_input = dict(tool_input)
    safe_input.pop("astrologer_id", None)
    safe_input["astrologer_id"] = ctx.astrologer_id

    try:
        return spec.handler(safe_input, ctx)
    except Exception:
        logger.exception("Tool execution failed for %s", tool_name)
        return ToolResult(
            content_for_model="error: tool execution failed",
            summary_for_trace=f"'{tool_name}' failed",
            is_error=True,
        )
