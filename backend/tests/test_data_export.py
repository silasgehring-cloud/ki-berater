"""DSGVO Art. 15 data export endpoint."""
from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

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


async def test_export_returns_all_tenant_data(integration_client: AsyncClient) -> None:
    shop = await _new_shop(integration_client, "export-shop.example.com")
    api = shop["api_key"]

    # Create some data: a product + a conversation (which generates llm_usage).
    await integration_client.post(
        "/v1/products",
        json={
            "external_id": "wc-1",
            "name": "Testschuh",
            "description": "x",
            "categories": ["Schuhe"],
            "stock_status": "instock",
        },
        headers={"X-Api-Key": api},
    )
    await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "Hallo"},
        headers={"X-Api-Key": api},
    )

    resp = await integration_client.get("/v1/shops/me/export", headers={"X-Api-Key": api})
    assert resp.status_code == 200
    body = resp.json()
    assert body["shop"]["domain"] == "export-shop.example.com"
    assert len(body["products"]) == 1
    assert len(body["conversations"]) == 1
    assert len(body["messages"]) == 2  # user + assistant
    assert len(body["llm_usage"]) == 1
    assert "exported_at" in body


async def test_export_strips_webhook_secret(integration_client: AsyncClient) -> None:
    shop = await _new_shop(integration_client, "secret-strip.example.com")
    resp = await integration_client.get(
        "/v1/shops/me/export", headers={"X-Api-Key": shop["api_key"]}
    )
    assert resp.status_code == 200
    config = resp.json()["shop"]["config"]
    assert "webhook_secret" not in config


async def test_export_is_tenant_scoped(integration_client: AsyncClient) -> None:
    shop_a = await _new_shop(integration_client, "tenant-a.example.com")
    shop_b = await _new_shop(integration_client, "tenant-b.example.com")
    # Shop A creates data.
    await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "A's secret data"},
        headers={"X-Api-Key": shop_a["api_key"]},
    )
    # Shop B's export must NOT contain it.
    export_b = await integration_client.get(
        "/v1/shops/me/export", headers={"X-Api-Key": shop_b["api_key"]}
    )
    assert export_b.status_code == 200
    body = export_b.json()
    assert body["shop"]["domain"] == "tenant-b.example.com"
    assert body["conversations"] == []
    assert body["messages"] == []


async def test_export_requires_auth(integration_client: AsyncClient) -> None:
    resp = await integration_client.get("/v1/shops/me/export")
    assert resp.status_code == 401
