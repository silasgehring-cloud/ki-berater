"""Hard-cap enforcement: 402 when monthly_conversations is exceeded."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.conversation import Conversation
from backend.models.shop import Shop
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


async def test_quota_endpoint_reports_zero_usage_for_new_shop(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "quota-fresh.example.com")
    resp = await integration_client.get(
        "/v1/billing/quota", headers={"X-Api-Key": shop["api_key"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "starter"
    assert body["monthly_conversations"] == 300
    assert body["used_in_period"] == 0
    assert body["remaining"] == 300


async def test_starter_402_when_300_conversations_in_period(
    integration_client: AsyncClient,
    db: AsyncSession,
) -> None:
    """Stuff 300 conversations in the rolling window, expect the 301st to 402."""
    shop_payload = await _new_shop(integration_client, "quota-cap.example.com")
    shop_id = shop_payload["id"]

    # Insert 300 conversations directly in the rolling 30-day window.
    now = datetime.now(UTC)
    db.add_all([
        Conversation(shop_id=shop_id, started_at=now - timedelta(hours=1))
        for _ in range(300)
    ])
    await db.commit()

    resp = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "should be blocked"},
        headers={"X-Api-Key": shop_payload["api_key"]},
    )
    assert resp.status_code == 402
    detail = resp.json()["detail"]
    assert detail["code"] == "quota_exceeded"


async def test_enterprise_plan_bypasses_quota(
    integration_client: AsyncClient,
    db: AsyncSession,
) -> None:
    shop_payload = await _new_shop(integration_client, "quota-ent.example.com")
    shop_id = shop_payload["id"]

    # Bump shop to enterprise.
    await db.execute(update(Shop).where(Shop.id == shop_id).values(plan="enterprise"))
    # Stuff lots of conversations.
    now = datetime.now(UTC)
    db.add_all([
        Conversation(shop_id=shop_id, started_at=now - timedelta(hours=1))
        for _ in range(10_000)
    ])
    await db.commit()

    resp = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "still allowed"},
        headers={"X-Api-Key": shop_payload["api_key"]},
    )
    assert resp.status_code == 201


async def test_existing_conversation_followups_not_counted_against_quota(
    integration_client: AsyncClient,
    db: AsyncSession,
) -> None:
    """The cap is on NEW conversations. Follow-up messages stay free."""
    shop_payload = await _new_shop(integration_client, "quota-follow.example.com")
    shop_id = shop_payload["id"]

    # Fill up the quota.
    now = datetime.now(UTC)
    db.add_all([
        Conversation(shop_id=shop_id, started_at=now - timedelta(hours=1))
        for _ in range(299)
    ])
    await db.commit()

    # Create the 300th conversation — still allowed.
    create = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "300th"},
        headers={"X-Api-Key": shop_payload["api_key"]},
    )
    assert create.status_code == 201
    convo_id = create.json()["conversation"]["id"]

    # New conversation now blocked.
    blocked = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "301st"},
        headers={"X-Api-Key": shop_payload["api_key"]},
    )
    assert blocked.status_code == 402

    # But the existing conversation can still receive follow-ups.
    follow = await integration_client.post(
        f"/v1/conversations/{convo_id}/messages",
        json={"content": "follow-up should pass"},
        headers={"X-Api-Key": shop_payload["api_key"]},
    )
    assert follow.status_code == 201
