"""Single source of truth for LLM model pricing in EUR per million tokens.

Prices are approximate and MUST be verified against provider pricing pages
before each release. Last reviewed: 2026-04-29.

Conversion to EUR is baked in (rough USD->EUR ~0.93 at time of writing) so
billing arithmetic stays in one currency.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ModelPricing:
    model_id: str
    input_eur_per_mtok: Decimal
    output_eur_per_mtok: Decimal
    cached_eur_per_mtok: Decimal


_PRICING: dict[str, ModelPricing] = {
    # Google
    "gemini-2.5-flash": ModelPricing(
        model_id="gemini-2.5-flash",
        input_eur_per_mtok=Decimal("0.28"),
        output_eur_per_mtok=Decimal("2.34"),
        cached_eur_per_mtok=Decimal("0.07"),
    ),
    "gemini-2.5-pro": ModelPricing(
        model_id="gemini-2.5-pro",
        input_eur_per_mtok=Decimal("1.17"),
        output_eur_per_mtok=Decimal("4.68"),
        cached_eur_per_mtok=Decimal("0.29"),
    ),
    "text-embedding-004": ModelPricing(
        model_id="text-embedding-004",
        input_eur_per_mtok=Decimal("0.019"),
        output_eur_per_mtok=Decimal("0"),
        cached_eur_per_mtok=Decimal("0.019"),
    ),
    # Anthropic
    "claude-sonnet-4-5": ModelPricing(
        model_id="claude-sonnet-4-5",
        input_eur_per_mtok=Decimal("2.81"),
        output_eur_per_mtok=Decimal("14.04"),
        cached_eur_per_mtok=Decimal("0.28"),
    ),
    "claude-haiku-4-5": ModelPricing(
        model_id="claude-haiku-4-5",
        input_eur_per_mtok=Decimal("0.94"),
        output_eur_per_mtok=Decimal("4.68"),
        cached_eur_per_mtok=Decimal("0.09"),
    ),
    # Mock for tests — zero cost.
    "mock-1": ModelPricing(
        model_id="mock-1",
        input_eur_per_mtok=Decimal("0"),
        output_eur_per_mtok=Decimal("0"),
        cached_eur_per_mtok=Decimal("0"),
    ),
}


def get_pricing(model_id: str) -> ModelPricing:
    if model_id not in _PRICING:
        raise KeyError(f"unknown model {model_id!r} — add to backend/llm/pricing.py")
    return _PRICING[model_id]


def estimate_cost_eur(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> Decimal:
    p = get_pricing(model_id)
    billable_input = max(0, input_tokens - cached_tokens)
    return (
        (Decimal(billable_input) * p.input_eur_per_mtok)
        + (Decimal(cached_tokens) * p.cached_eur_per_mtok)
        + (Decimal(output_tokens) * p.output_eur_per_mtok)
    ) / Decimal(1_000_000)
