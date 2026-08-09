"""Thin wrapper around the Gemini SDK so the orchestrator depends on one
narrow interface (`generate`) that tests can swap for a fake — never on the
SDK client directly.
"""

from typing import Protocol

from google import genai
from google.genai import types

from app.core.config import settings


class AgentClient(Protocol):
    def generate(
        self, *, system: str, contents: list[types.Content], tools: list[types.Tool]
    ) -> types.GenerateContentResponse:
        ...


class GeminiAgentClient:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

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
            ),
        )


def get_agent_client() -> AgentClient:
    return GeminiAgentClient()
