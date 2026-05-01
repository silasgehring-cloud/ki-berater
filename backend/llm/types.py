"""Provider-agnostic message and result types.

These shapes are the contract between `services/conversation_service` and
every `LLMProvider`. Providers translate to/from their native SDK types but
the orchestration layer never sees Anthropic/Google specifics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class CompletionResult:
    text: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    model_id: str
    provider: str
    latency_ms: int


@dataclass(frozen=True)
class StreamChunk:
    """One step of a streaming completion.

    For mid-stream events, `delta` carries text and `final` is None.
    For the final event, `delta == ""` and `final` carries the totals
    (input/output/cached tokens, model id, latency, provider).
    """

    delta: str
    final: CompletionResult | None = None
