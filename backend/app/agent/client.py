"""Thin wrapper around the Gemini SDK so the orchestrator depends on one
narrow interface (`generate`) that tests can swap for a fake — never on the
SDK client directly.
"""

from typing import Protocol

from google.genai import types

from app.agent import vertex_client
from app.core.config import settings

# Placeholder pending the exact key/value ops wants for billing attribution
# (2026-08-18) — passed through to Vertex AI's own request, which breaks
# billed cost down by these labels. Update once given the real spec; every
# call from the main chat loop carries this same label.
_BILLING_LABELS = {"flow": "chat"}


class AgentClient(Protocol):
    def generate(
        self, *, system: str, contents: list[types.Content], tools: list[types.Tool]
    ) -> types.GenerateContentResponse:
        ...


class GeminiAgentClient:
    def __init__(self) -> None:
        self._client = vertex_client.build_vertex_client()

    def generate(
        self, *, system: str, contents: list[types.Content], tools: list[types.Tool]
    ) -> types.GenerateContentResponse:
        return self._client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                tools=tools,
                max_output_tokens=2048,
                labels=_BILLING_LABELS,
            ),
        )


def get_agent_client() -> AgentClient:
    return GeminiAgentClient()
