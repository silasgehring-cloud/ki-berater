"""Single source of truth for Plan-Limits + Stripe-Price-Mapping.

Hard-cap semantics (decided in the plan): when a shop reaches its monthly
conversation quota, further requests return HTTP 402 Payment Required with
a hint to upgrade. Re-counts at the start of each Stripe billing period.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.core.config import settings


@dataclass(frozen=True)
class PlanLimits:
    plan: str
    monthly_eur: int
    monthly_conversations: int | None  # None = unlimited (Enterprise)
    stripe_price_id: str  # empty for enterprise / unconfigured


def _plan(plan: str, eur: int, convos: int | None, price_id: str) -> PlanLimits:
    return PlanLimits(plan=plan, monthly_eur=eur, monthly_conversations=convos,
                      stripe_price_id=price_id)


def all_plans() -> dict[str, PlanLimits]:
    """Read at call time so settings overrides take effect."""
    return {
        "starter":    _plan("starter",    39,  300,  settings.stripe_price_starter),
        "growth":     _plan("growth",     129, 1500, settings.stripe_price_growth),
        "pro":        _plan("pro",        349, 5000, settings.stripe_price_pro),
        "enterprise": _plan("enterprise", 999, None, settings.stripe_price_enterprise),
    }


def get_plan(plan: str) -> PlanLimits:
    plans = all_plans()
    if plan not in plans:
        raise KeyError(f"unknown plan {plan!r} — must be one of {list(plans)}")
    return plans[plan]
