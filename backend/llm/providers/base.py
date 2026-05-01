"""LLM Provider Protocol — the only sanctioned LLM call surface.

CRITICAL ANTI-PATTERN: Do NOT instantiate Anthropic/Google SDK clients outside
this package. The router + cost_tracker depend on every call going through a
Provider so usage is always recorded.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from backend.llm.types import ChatMessage, CompletionResult, StreamChunk


class ProviderError(Exception):
    """Raised when a provider call fails. Triggers fallback chain."""


@runtime_checkable
class LLMProvider(Protocol):
    name: str
    model_id: str

    async def complete(
        self,
        system: str,
        history: list[ChatMessage],
    ) -> CompletionResult: ...

    def stream(
        self,
        system: str,
        history: list[ChatMessage],
    ) -> AsyncIterator[StreamChunk]: ...
