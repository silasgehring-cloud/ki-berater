"""Anthropic Claude provider with ephemeral prompt caching on the system block."""
from __future__ import annotations

import time
from collections.abc import AsyncIterator

import anthropic
from anthropic import APIError

from backend.llm.providers.base import LLMProvider, ProviderError
from backend.llm.types import ChatMessage, CompletionResult, StreamChunk


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model_id: str = "claude-sonnet-4-5") -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model_id = model_id

    async def complete(
        self, system: str, history: list[ChatMessage]
    ) -> CompletionResult:
        start = time.perf_counter()
        try:
            resp = await self._client.messages.create(
                model=self.model_id,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {"role": m.role, "content": m.content} for m in history
                ],
            )
        except APIError as exc:
            raise ProviderError(f"anthropic call failed: {exc}") from exc

        text = "".join(block.text for block in resp.content if block.type == "text")
        usage = resp.usage
        cached = (
            getattr(usage, "cache_read_input_tokens", 0) or 0
        ) + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
        return CompletionResult(
            text=text,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=cached,
            model_id=self.model_id,
            provider=self.name,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    async def stream(
        self, system: str, history: list[ChatMessage]
    ) -> AsyncIterator[StreamChunk]:
        start = time.perf_counter()
        full_text_parts: list[str] = []
        try:
            async with self._client.messages.stream(
                model=self.model_id,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {"role": m.role, "content": m.content} for m in history
                ],
            ) as stream:
                async for delta in stream.text_stream:
                    full_text_parts.append(delta)
                    yield StreamChunk(delta=delta)
                final_msg = await stream.get_final_message()
        except APIError as exc:
            raise ProviderError(f"anthropic stream failed: {exc}") from exc

        usage = final_msg.usage
        cached = (
            getattr(usage, "cache_read_input_tokens", 0) or 0
        ) + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
        yield StreamChunk(
            delta="",
            final=CompletionResult(
                text="".join(full_text_parts),
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_tokens=cached,
                model_id=self.model_id,
                provider=self.name,
                latency_ms=int((time.perf_counter() - start) * 1000),
            ),
        )
