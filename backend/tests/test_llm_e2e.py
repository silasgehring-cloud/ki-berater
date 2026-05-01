"""End-to-end: a conversation gets persisted alongside an llm_usage row.

This is the smoke test the plan asked for: "POST /v1/conversations triggers
LLM, llm_usage row contains tokens + cost".
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.llm_usage import LLMUsage
from backend.models.message import Message
from backend.tests.conftest import TEST_ADMIN_KEY

pytestmark = pytest.mark.integration


async def _new_shop(client: AsyncClient, domain: str) -> str:
    resp = await client.post(
        "/v1/shops",
        json={"domain": domain},
        headers={"X-Admin-Key": TEST_ADMIN_KEY},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["api_key"])


async def test_create_conversation_writes_llm_usage_row(
    integration_client: AsyncClient,
    db: AsyncSession,
) -> None:
    api_key = await _new_shop(integration_client, "e2e-shop.example.com")
    create = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "Welche Schuhe für Plattfüße?"},
        headers={"X-Api-Key": api_key},
    )
    assert create.status_code == 201

    rows = (await db.execute(select(LLMUsage))).scalars().all()
    assert len(rows) == 1
    usage = rows[0]
    assert usage.model == "mock-1"
    assert usage.input_tokens > 0
    assert usage.output_tokens > 0
    assert usage.cost_eur == Decimal("0")  # mock model has zero pricing
    assert usage.latency_ms >= 0


async def test_followup_message_writes_second_usage_row(
    integration_client: AsyncClient,
    db: AsyncSession,
) -> None:
    api_key = await _new_shop(integration_client, "e2e-shop2.example.com")
    create = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "Hallo"},
        headers={"X-Api-Key": api_key},
    )
    convo_id = create.json()["conversation"]["id"]
    await integration_client.post(
        f"/v1/conversations/{convo_id}/messages",
        json={"content": "Folgefrage"},
        headers={"X-Api-Key": api_key},
    )

    usage_count = len((await db.execute(select(LLMUsage))).scalars().all())
    assert usage_count == 2

    msgs = list((await db.execute(select(Message).order_by(Message.created_at))).scalars().all())
    # 2 user + 2 assistant
    assert [m.role for m in msgs] == ["user", "assistant", "user", "assistant"]
