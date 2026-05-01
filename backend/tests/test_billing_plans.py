"""Plan-Limits config + lookup. Pure unit tests."""
import pytest

from backend.billing.plans import all_plans, get_plan


def test_all_four_plans_present() -> None:
    plans = all_plans()
    assert set(plans) == {"starter", "growth", "pro", "enterprise"}


def test_starter_has_300_conversations() -> None:
    assert get_plan("starter").monthly_conversations == 300


def test_growth_has_1500() -> None:
    assert get_plan("growth").monthly_conversations == 1500


def test_pro_has_5000() -> None:
    assert get_plan("pro").monthly_conversations == 5000


def test_enterprise_is_unlimited() -> None:
    assert get_plan("enterprise").monthly_conversations is None


def test_unknown_plan_raises() -> None:
    with pytest.raises(KeyError):
        get_plan("platinum")


def test_pricing_matches_spec() -> None:
    assert get_plan("starter").monthly_eur == 39
    assert get_plan("growth").monthly_eur == 129
    assert get_plan("pro").monthly_eur == 349
