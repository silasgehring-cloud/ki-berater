"""Google Gemini provider. Implicit caching kicks in for >2k repeated tokens."""
from __future__ import annotations

import time
from collections.abc import AsyncIterator

from google import genai
from google.genai import types as genai_types

from backend.llm.providers.base import LLMProvider, ProviderError
from backend.llm.types import ChatMessage, CompletionResult, StreamChunk


class GoogleProvider(LLMProvider):
    name = "google"

    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash") -> None:
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not configured")
        self._client = genai.Client(api_key=api_key)
        self.model_id = model_id

    async def complete(
        self, system: str, history: list[ChatMessage]
    ) -> CompletionResult:
        start = time.perf_counter()
        contents = [
            genai_types.Content(
                role="user" if m.role == "user" else "model",
                parts=[genai_types.Part(text=m.content)],
            )
            for m in history
        ]
        try:
            resp = await self._client.aio.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=2048,
                ),
            )
        except Exception as exc:
            raise ProviderError(f"google call failed: {exc}") from exc

        text = resp.text or ""
        usage = resp.usage_metadata
        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0
        cached_tokens = getattr(usage, "cached_content_token_count", 0) or 0
        return CompletionResult(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            model_id=self.model_id,
            provider=self.name,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    async def stream(
        self, system: str, history: list[ChatMessage]
    ) -> AsyncIterator[StreamChunk]:
        start = time.perf_counter()
        contents = [
            genai_types.Content(
                role="user" if m.role == "user" else "model",
                parts=[genai_types.Part(text=m.content)],
            )
            for m in history
        ]
        full_text_parts: list[str] = []
        last_usage = None
        try:
            stream = await self._client.aio.models.generate_content_stream(
                model=self.model_id,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=2048,
                ),
            )
            async for chunk in stream:
                delta = chunk.text or ""
                if delta:
                    full_text_parts.append(delta)
                    yield StreamChunk(delta=delta)
                if getattr(chunk, "usage_metadata", None) is not None:
                    last_usage = chunk.usage_metadata
        except Exception as exc:
            raise ProviderError(f"google stream failed: {exc}") from exc

        input_tokens = getattr(last_usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(last_usage, "candidates_token_count", 0) or 0
        cached_tokens = getattr(last_usage, "cached_content_token_count", 0) or 0
        yield StreamChunk(
            delta="",
            final=CompletionResult(
                text="".join(full_text_parts),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
                model_id=self.model_id,
                provider=self.name,
                latency_ms=int((time.perf_counter() - start) * 1000),
            ),
        )
