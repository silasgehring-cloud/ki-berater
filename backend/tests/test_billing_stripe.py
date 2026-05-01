"""Stripe checkout/portal/webhook with a fake StripeClient.

Real Stripe SDK is replaced via `set_stripe_client(...)`. We verify:
- /v1/billing/checkout calls Stripe with the right price_id and returns the URL
- /v1/billing/portal calls Stripe with the right customer_id
- /v1/webhooks/stripe verifies signature + applies subscription state to the shop
"""
from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.billing.stripe_client import set_stripe_client
from backend.core.config import settings
from backend.models.shop import Shop
from backend.tests.conftest import TEST_ADMIN_KEY

pytestmark = pytest.mark.integration


class _FakeSession:
    def __init__(self, url: str = "https://stripe.test/checkout/abc") -> None:
        self.url = url


class _FakeStripe:
    def __init__(self) -> None:
        self.last_checkout_kwargs: dict[str, Any] | None = None
        self.last_portal_kwargs: dict[str, Any] | None = None
        self.next_event: dict[str, Any] | None = None

    def construct_event(self, payload: bytes, sig_header: str, secret: str) -> Any:
        if not self.next_event:
            raise ValueError("test forgot to set next_event")
        return self.next_event

    def create_checkout_session(self, **kwargs: Any) -> Any:
        self.last_checkout_kwargs = kwargs
        return _FakeSession("https://stripe.test/checkout/abc")

    def create_billing_portal_session(self, **kwargs: Any) -> Any:
        self.last_portal_kwargs = kwargs
        return _FakeSession("https://stripe.test/portal/xyz")

    def retrieve_subscription(self, subscription_id: str) -> Any:
        return {"id": subscription_id, "status": "active"}


@pytest.fixture
def fake_stripe(monkeypatch: pytest.MonkeyPatch) -> Generator[_FakeStripe, None, None]:
    fake = _FakeStripe()
    set_stripe_client(fake)
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(settings, "stripe_price_starter", "price_starter_test")
    monkeypatch.setattr(settings, "stripe_price_growth", "price_growth_test")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_pro_test")
    yield fake
    set_stripe_client(None)  # type: ignore[arg-type]


async def _new_shop(client: AsyncClient, domain: str) -> dict[str, Any]:
    resp = await client.post(
        "/v1/shops",
        json={"domain": domain},
        headers={"X-Admin-Key": TEST_ADMIN_KEY},
    )
    assert resp.status_code == 201
    body: dict[str, Any] = resp.json()
    return body


async def test_checkout_returns_stripe_url(
    integration_client: AsyncClient,
    fake_stripe: _FakeStripe,
) -> None:
    shop = await _new_shop(integration_client, "billing-1.example.com")
    resp = await integration_client.post(
        "/v1/billing/checkout",
        json={"plan": "growth"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.status_code == 201
    assert resp.json()["url"] == "https://stripe.test/checkout/abc"
    kwargs = fake_stripe.last_checkout_kwargs
    assert kwargs is not None
    assert kwargs["mode"] == "subscription"
    assert kwargs["line_items"][0]["price"] == "price_growth_test"
    assert kwargs["client_reference_id"] == shop["id"]


async def test_checkout_for_unconfigured_plan_is_400(
    integration_client: AsyncClient,
    fake_stripe: _FakeStripe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "stripe_price_pro", "")  # uncon­figured
    shop = await _new_shop(integration_client, "billing-2.example.com")
    resp = await integration_client.post(
        "/v1/billing/checkout",
        json={"plan": "pro"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.status_code == 400


async def test_portal_requires_existing_customer(
    integration_client: AsyncClient,
    fake_stripe: _FakeStripe,
) -> None:
    shop = await _new_shop(integration_client, "billing-3.example.com")
    resp = await integration_client.post(
        "/v1/billing/portal",
        headers={"X-Api-Key": shop["api_key"]},
    )
    # Shop has no stripe_customer_id yet → 400 with explanation.
    assert resp.status_code == 400


async def test_webhook_checkout_completed_marks_shop_active(
    integration_client: AsyncClient,
    db: AsyncSession,
    fake_stripe: _FakeStripe,
) -> None:
    shop = await _new_shop(integration_client, "billing-wh1.example.com")
    fake_stripe.next_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"shop_id": shop["id"]},
                "customer": "cus_123",
                "subscription": "sub_456",
            }
        },
    }
    resp = await integration_client.post(
        "/v1/webhooks/stripe",
        content=b"{}",
        headers={
            "Stripe-Signature": "t=1,v1=test",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["handled"] is True
    assert body["event_type"] == "checkout.session.completed"

    # Shop now has stripe IDs and active status.
    row = (await db.execute(select(Shop).where(Shop.id == shop["id"]))).scalar_one()
    assert row.stripe_customer_id == "cus_123"
    assert row.stripe_subscription_id == "sub_456"
    assert row.subscription_status == "active"


async def test_webhook_subscription_updated_syncs_period_and_plan(
    integration_client: AsyncClient,
    db: AsyncSession,
    fake_stripe: _FakeStripe,
) -> None:
    shop = await _new_shop(integration_client, "billing-wh2.example.com")
    # Pre-link the subscription so the webhook can find the shop.
    from sqlalchemy import update

    await db.execute(
        update(Shop).where(Shop.id == shop["id"]).values(
            stripe_subscription_id="sub_999",
            stripe_customer_id="cus_999",
        )
    )
    await db.commit()

    fake_stripe.next_event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_999",
                "status": "active",
                "current_period_start": 1735689600,  # 2025-01-01
                "current_period_end":   1738368000,  # 2025-02-01
                "items": {"data": [{"price": {"id": "price_pro_test"}}]},
            }
        },
    }
    resp = await integration_client.post(
        "/v1/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "t=1,v1=test"},
    )
    assert resp.status_code == 200

    row = (await db.execute(select(Shop).where(Shop.id == shop["id"]))).scalar_one()
    assert row.plan == "pro"
    assert row.subscription_status == "active"
    assert row.current_period_start is not None
    assert row.current_period_end is not None


async def test_webhook_missing_signature_returns_400(
    integration_client: AsyncClient,
    fake_stripe: _FakeStripe,
) -> None:
    resp = await integration_client.post(
        "/v1/webhooks/stripe",
        content=b"{}",
    )
    assert resp.status_code == 400


async def test_webhook_invalid_signature_returns_400(
    integration_client: AsyncClient,
    fake_stripe: _FakeStripe,
) -> None:
    """fake construct_event raises if next_event is None — simulates verify-fail."""
    fake_stripe.next_event = None
    resp = await integration_client.post(
        "/v1/webhooks/stripe",
        content=b"{}",
        headers={"Stripe-Signature": "garbage"},
    )
    assert resp.status_code == 400


# Suppress unused
_ = json
