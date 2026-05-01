"""Pricing math + lookup. Pure unit tests, no DB."""
from decimal import Decimal

import pytest

from backend.llm.pricing import estimate_cost_eur, get_pricing


def test_known_models_have_pricing() -> None:
    for model in [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        "text-embedding-004",
        "mock-1",
    ]:
        assert get_pricing(model).model_id == model


def test_unknown_model_raises() -> None:
    with pytest.raises(KeyError):
        get_pricing("does-not-exist")


def test_cost_zero_for_mock() -> None:
    assert estimate_cost_eur("mock-1", 1000, 500, 0) == Decimal("0")


def test_cost_uses_cached_rate_for_cached_tokens() -> None:
    # Sonnet input 2.81 €/Mtok, cache read 0.28 €/Mtok.
    full = estimate_cost_eur("claude-sonnet-4-5", 1_000_000, 0, 0)
    half_cached = estimate_cost_eur("claude-sonnet-4-5", 1_000_000, 0, 500_000)
    assert half_cached < full
    # 500k @ 2.81 + 500k @ 0.28 = 1.405 + 0.14 = 1.545
    assert half_cached == pytest.approx(Decimal("1.545"), abs=Decimal("0.01"))


def test_cost_includes_output_tokens() -> None:
    # Flash output 2.34 €/Mtok.
    cost = estimate_cost_eur("gemini-2.5-flash", 0, 1_000_000, 0)
    assert cost == Decimal("2.34")


def test_typical_conversation_cost_is_under_5_cents() -> None:
    # ~2k input tokens (system+history), ~500 output tokens, all cached input.
    cost = estimate_cost_eur(
        "gemini-2.5-flash",
        input_tokens=2000,
        output_tokens=500,
        cached_tokens=2000,
    )
    # Expect well under €0.05 per turn.
    assert cost < Decimal("0.05")
