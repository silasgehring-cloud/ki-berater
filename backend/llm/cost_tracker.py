"""Persist every LLM call into the `llm_usage` table.

This MUST be called for every completion or we lose margin visibility.
The router logs usage; this module turns logs into rows.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.llm.pricing import estimate_cost_eur
from backend.llm.types import CompletionResult
from backend.models.llm_usage import LLMUsage


async def record_usage(
    db: AsyncSession,
    *,
    shop_id: UUID,
    conversation_id: UUID | None,
    result: CompletionResult,
) -> LLMUsage:
    cost = estimate_cost_eur(
        model_id=result.model_id,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cached_tokens=result.cached_tokens,
    )
    row = LLMUsage(
        shop_id=shop_id,
        conversation_id=conversation_id,
        model=result.model_id,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cached_tokens=result.cached_tokens,
        cost_eur=cost,
        latency_ms=result.latency_ms,
    )
    db.add(row)
    return row
