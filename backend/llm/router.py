"""LLM-Router — heuristic complexity detection + fallback chain.

Routing decision (Sprint 1.2: heuristik-first; ML-classifier later):
  - "complex"  -> Claude Sonnet  -> Gemini Pro -> Haiku  (high reasoning need)
  - "standard" -> Gemini Flash   -> Claude Haiku        (80% of traffic)

A request is "complex" if:
  - last user message hits a complexity keyword (vergleich, unterschied, ...)
  - OR conversation history exceeds ~4000 chars (proxy for token budget)
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal

import structlog

from backend.llm.providers.base import LLMProvider, ProviderError
from backend.llm.types import ChatMessage, CompletionResult, StreamChunk

logger = structlog.get_logger("backend.llm.router")

Complexity = Literal["standard", "complex"]

COMPLEX_KEYWORDS: tuple[str, ...] = (
    "vergleich",
    "unterschied",
    "passt für",
    "passt zu mir",
    "empfehl",
    "welche soll",
    "welcher soll",
    "welches soll",
    "beratung",
    "compare",
    "difference",
    "recommend",
)

_COMPLEX_HISTORY_CHARS = 4000


def classify_complexity(history: list[ChatMessage]) -> Complexity:
    if sum(len(m.content) for m in history) > _COMPLEX_HISTORY_CHARS:
        return "complex"
    last_user = next((m for m in reversed(history) if m.role == "user"), None)
    if last_user is None:
        return "standard"
    text = last_user.content.lower()
    if any(kw in text for kw in COMPLEX_KEYWORDS):
        return "complex"
    return "standard"


class AllProvidersFailedError(Exception):
    """Raised when every provider in the fallback chain failed."""


class Router:
    def __init__(
        self,
        providers: dict[str, LLMProvider],
        chains: dict[Complexity, list[str]],
    ) -> None:
        self.providers = providers
        self.chains = chains

    async def complete(
        self,
        system: str,
        history: list[ChatMessage],
        complexity: Complexity | None = None,
    ) -> CompletionResult:
        complexity = complexity or classify_complexity(history)
        chain = self.chains.get(complexity, [])
        if not chain:
            raise AllProvidersFailedError(f"no providers for complexity {complexity!r}")

        last_error: Exception | None = None
        for provider_id in chain:
            provider = self.providers.get(provider_id)
            if provider is None:
                continue
            try:
                result = await provider.complete(system, history)
                logger.info(
                    "llm.complete",
                    provider=provider.name,
                    model=result.model_id,
                    complexity=complexity,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    cached_tokens=result.cached_tokens,
                    latency_ms=result.latency_ms,
                )
                return result
            except ProviderError as exc:
                logger.warning(
                    "llm.fallback",
                    provider=provider_id,
                    complexity=complexity,
                    reason=str(exc),
                )
                last_error = exc
                continue

        raise AllProvidersFailedError(
            f"all providers in chain {chain!r} failed; last={last_error!r}"
        )

    async def stream(
        self,
        system: str,
        history: list[ChatMessage],
        complexity: Complexity | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream chunks. Fallback only fires BEFORE the first delta is emitted —
        once the client started seeing tokens, switching providers mid-stream
        would corrupt the answer."""
        complexity = complexity or classify_complexity(history)
        chain = self.chains.get(complexity, [])
        if not chain:
            raise AllProvidersFailedError(f"no providers for complexity {complexity!r}")

        last_error: Exception | None = None
        for provider_id in chain:
            provider = self.providers.get(provider_id)
            if provider is None:
                continue

            emitted_any = False
            try:
                async for chunk in provider.stream(system, history):
                    emitted_any = True
                    yield chunk
                    if chunk.final is not None:
                        logger.info(
                            "llm.stream.complete",
                            provider=provider.name,
                            model=chunk.final.model_id,
                            input_tokens=chunk.final.input_tokens,
                            output_tokens=chunk.final.output_tokens,
                            cached_tokens=chunk.final.cached_tokens,
                            latency_ms=chunk.final.latency_ms,
                        )
                return
            except ProviderError as exc:
                last_error = exc
                if emitted_any:
                    # Already streamed partial output — cannot safely retry.
                    raise
                logger.warning(
                    "llm.stream.fallback",
                    provider=provider_id,
                    complexity=complexity,
                    reason=str(exc),
                )
                continue

        raise AllProvidersFailedError(
            f"all providers in stream chain {chain!r} failed; last={last_error!r}"
        )
