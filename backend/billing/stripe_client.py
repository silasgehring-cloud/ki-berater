"""Thin wrapper around the stripe SDK.

All Stripe operations go through this module so tests can override `_get_client()`
without touching every call-site. ProductionStripe is HTTP — tests use the
mock provided by stripe-mock or raw monkeypatching of `_module.stripe`.
"""
from __future__ import annotations

from typing import Any, Protocol

import stripe

from backend.core.config import settings


class StripeClient(Protocol):
    """Subset of stripe SDK we use — kept narrow so tests can fake it."""

    def construct_event(
        self, payload: bytes, sig_header: str, secret: str
    ) -> Any: ...

    def create_checkout_session(self, **kwargs: Any) -> Any: ...

    def create_billing_portal_session(self, **kwargs: Any) -> Any: ...

    def retrieve_subscription(self, subscription_id: str) -> Any: ...


class _RealStripeClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise RuntimeError("STRIPE_API_KEY not configured")
        stripe.api_key = api_key

    def construct_event(
        self, payload: bytes, sig_header: str, secret: str
    ) -> Any:
        return stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload, sig_header, secret
        )

    def create_checkout_session(self, **kwargs: Any) -> Any:
        return stripe.checkout.Session.create(**kwargs)

    def create_billing_portal_session(self, **kwargs: Any) -> Any:
        return stripe.billing_portal.Session.create(**kwargs)

    def retrieve_subscription(self, subscription_id: str) -> Any:
        return stripe.Subscription.retrieve(subscription_id)


_singleton: StripeClient | None = None


def get_stripe_client() -> StripeClient:
    global _singleton
    if _singleton is None:
        _singleton = _RealStripeClient(settings.stripe_api_key)
    return _singleton


def set_stripe_client(client: StripeClient) -> None:
    """Test hook to inject a fake client."""
    global _singleton
    _singleton = client
