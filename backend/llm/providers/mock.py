"""Deterministic provider for tests. Records calls for assertions."""
from __future__ import annotations

import time
from collections.abc import AsyncIterator

from backend.llm.providers.base import LLMProvider, ProviderError
from backend.llm.types import ChatMessage, CompletionResult, StreamChunk


class MockProvider(LLMProvider):
    name = "mock"
    model_id = "mock-1"

    def __init__(
        self,
        response: str = "Mock answer.",
        raise_error: bool = False,
        cached_tokens: int = 0,
        stream_chunk_size: int = 5,
    ) -> None:
        self._response = response
        self._raise = raise_error
        self._cached_tokens = cached_tokens
        self._chunk_size = max(1, stream_chunk_size)
        self.calls: list[tuple[str, list[ChatMessage]]] = []
        self.stream_calls: list[tuple[str, list[ChatMessage]]] = []

    async def complete(
        self, system: str, history: list[ChatMessage]
    ) -> CompletionResult:
        self.calls.append((system, history))
        if self._raise:
            raise ProviderError("mock provider configured to fail")
        # Cheap deterministic token estimates: 1 token ~= 4 chars.
        input_tokens = (len(system) + sum(len(m.content) for m in history)) // 4
        output_tokens = max(1, len(self._response) // 4)
        start = time.perf_counter()
        latency_ms = int((time.perf_counter() - start) * 1000)
        return CompletionResult(
            text=self._response,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=self._cached_tokens,
            model_id=self.model_id,
            provider=self.name,
            latency_ms=latency_ms,
        )

    async def stream(
        self, system: str, history: list[ChatMessage]
    ) -> AsyncIterator[StreamChunk]:
        self.stream_calls.append((system, history))
        if self._raise:
            raise ProviderError("mock provider configured to fail")

        start = time.perf_counter()
        text = self._response
        chunks = [
            text[i : i + self._chunk_size] for i in range(0, len(text), self._chunk_size)
        ]
        for piece in chunks:
            yield StreamChunk(delta=piece)

        input_tokens = (len(system) + sum(len(m.content) for m in history)) // 4
        output_tokens = max(1, len(text) // 4)
        latency_ms = int((time.perf_counter() - start) * 1000)
        yield StreamChunk(
            delta="",
            final=CompletionResult(
                text=text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=self._cached_tokens,
                model_id=self.model_id,
                provider=self.name,
                latency_ms=latency_ms,
            ),
        )
