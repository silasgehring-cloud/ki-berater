"""Analytics overview math + tenant isolation."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.conversation import Conversation
from backend.models.llm_usage import LLMUsage
from backend.tests.conftest import TEST_ADMIN_KEY

pytestmark = pytest.mark.integration


async def _new_shop(client: AsyncClient, domain: str) -> dict[str, Any]:
    resp = await client.post(
        "/v1/shops",
        json={"domain": domain},
        headers={"X-Admin-Key": TEST_ADMIN_KEY},
    )
    assert resp.status_code == 201
    body: dict[str, Any] = resp.json()
    return body


async def test_overview_for_fresh_shop_is_all_zero(integration_client: AsyncClient) -> None:
    shop = await _new_shop(integration_client, "ana-fresh.example.com")
    resp = await integration_client.get(
        "/v1/analytics/overview",
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversations"]["total"] == 0
    assert body["conversations"]["converted"] == 0
    assert body["conversations"]["conversion_rate_percent"] == 0.0
    assert Decimal(body["revenue"]["total_eur"]) == Decimal("0")
    assert Decimal(body["llm_cost_eur"]) == Decimal("0")
    assert body["period"]["days"] == 30


async def test_overview_aggregates_correctly(
    integration_client: AsyncClient,
    db: AsyncSession,
) -> None:
    shop = await _new_shop(integration_client, "ana-math.example.com")
    shop_id = shop["id"]
    now = datetime.now(UTC)

    # 10 conversations: 3 converted with EUR totals 50, 100, 200 (= 350).
    convos: list[Conversation] = []
    for i in range(10):
        c = Conversation(
            shop_id=shop_id,
            started_at=now - timedelta(hours=i),
            converted=False,
        )
        convos.append(c)
        db.add(c)
    await db.flush()

    totals = (Decimal("50.00"), Decimal("100.00"), Decimal("200.00"))
    for c, total in zip(convos[:3], totals, strict=True):
        c.converted = True
        c.converted_at = now
        c.order_id = f"o-{c.id}"
        c.order_total_eur = total
        c.order_currency = "EUR"

    # Some llm_usage rows: total cost = 1.23
    db.add_all([
        LLMUsage(
            shop_id=shop_id, conversation_id=convos[0].id, model="mock-1",
            input_tokens=100, output_tokens=50, cached_tokens=0,
            cost_eur=Decimal("0.50"), latency_ms=100, created_at=now,
        ),
        LLMUsage(
            shop_id=shop_id, conversation_id=convos[1].id, model="mock-1",
            input_tokens=100, output_tokens=50, cached_tokens=0,
            cost_eur=Decimal("0.73"), latency_ms=120, created_at=now,
        ),
    ])
    await db.commit()

    resp = await integration_client.get(
        "/v1/analytics/overview",
        headers={"X-Api-Key": shop["api_key"]},
    )
    body = resp.json()
    assert body["conversations"]["total"] == 10
    assert body["conversations"]["converted"] == 3
    assert body["conversations"]["conversion_rate_percent"] == 30.0
    assert Decimal(body["revenue"]["total_eur"]) == Decimal("350.00")
    assert Decimal(body["llm_cost_eur"]) == Decimal("1.23")


async def test_overview_is_tenant_scoped(
    integration_client: AsyncClient,
    db: AsyncSession,
) -> None:
    shop_a = await _new_shop(integration_client, "ana-tenant-a.example.com")
    shop_b = await _new_shop(integration_client, "ana-tenant-b.example.com")
    now = datetime.now(UTC)

    # Lots of converted conversations on shop A.
    db.add_all([
        Conversation(
            shop_id=shop_a["id"],
            started_at=now,
            converted=True,
            converted_at=now,
            order_id=f"a-{i}",
            order_total_eur=Decimal("100.00"),
            order_currency="EUR",
        )
        for i in range(50)
    ])
    await db.commit()

    overview_b = await integration_client.get(
        "/v1/analytics/overview",
        headers={"X-Api-Key": shop_b["api_key"]},
    )
    body = overview_b.json()
    assert body["conversations"]["total"] == 0
    assert Decimal(body["revenue"]["total_eur"]) == Decimal("0")


async def test_overview_days_param_narrows_window(
    integration_client: AsyncClient,
    db: AsyncSession,
) -> None:
    shop = await _new_shop(integration_client, "ana-days.example.com")
    now = datetime.now(UTC)

    db.add_all([
        Conversation(shop_id=shop["id"], started_at=now - timedelta(days=2)),  # within 7d
        Conversation(shop_id=shop["id"], started_at=now - timedelta(days=20)),  # outside 7d
    ])
    await db.commit()

    resp = await integration_client.get(
        "/v1/analytics/overview?days=7",
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.json()["conversations"]["total"] == 1
    assert resp.json()["period"]["days"] == 7


async def test_overview_requires_auth(integration_client: AsyncClient) -> None:
    resp = await integration_client.get("/v1/analytics/overview")
    assert resp.status_code == 401


async def test_overview_rejects_invalid_days(integration_client: AsyncClient) -> None:
    shop = await _new_shop(integration_client, "ana-bad-days.example.com")
    resp = await integration_client.get(
        "/v1/analytics/overview?days=0",
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.status_code == 422
