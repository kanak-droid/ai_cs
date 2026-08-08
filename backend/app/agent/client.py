"""Thin wrapper around the Anthropic SDK so the orchestrator depends on one
narrow interface (`create`) that tests can swap for a fake — never on the SDK
client directly.
"""

from typing import Protocol

import anthropic

from app.core.config import settings


class AgentClient(Protocol):
    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> anthropic.types.Message:
        ...


class AnthropicAgentClient:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> anthropic.types.Message:
        return self._client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=2048,
            system=system,
            messages=messages,
            tools=tools,
        )


def get_agent_client() -> AgentClient:
    return AnthropicAgentClient()
