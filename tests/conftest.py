"""Shared fixtures for tests."""

from __future__ import annotations

from typing import Any, Callable

import pytest

from agent_pentest.client import ChatCallResult
from agent_pentest.config import EndpointConfig, PentestConfig
from agent_pentest.types import Message


class FakeClient:
    """In-memory test double satisfying the :class:`ChatClient` protocol.

    Intercepts ``chat`` and dispatches to a user-provided callable that
    receives the messages and returns a :class:`ChatCallResult`.
    """

    def __init__(
        self,
        responder: Callable[[list[Message], dict[str, Any]], ChatCallResult],
    ) -> None:
        self.cfg = EndpointConfig(model="fake")
        self.responder = responder
        self.calls: list[dict[str, Any]] = []

    async def chat(
        self,
        messages: list[Message],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatCallResult:
        ctx = {"tools": tools, "temperature": temperature, "max_tokens": max_tokens}
        self.calls.append({"messages": messages, **ctx})
        return self.responder(messages, ctx)

    async def aclose(self) -> None:  # noqa: D401 - stub
        return None


@pytest.fixture
def base_config() -> PentestConfig:
    return PentestConfig(
        target=EndpointConfig(model="target-model"),
        attacker=EndpointConfig(model="attacker-model"),
        judge=EndpointConfig(model="judge-model"),
        attempts_per_technique=1,
        max_turns=2,
        concurrency=2,
    )
