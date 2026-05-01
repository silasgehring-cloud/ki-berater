"""Product upsert, bulk-sync, status. Also verifies tenant isolation on products."""
from __future__ import annotations

import asyncio
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
    assert resp.status_code == 201, resp.text
    body: dict[str, Any] = resp.json()
    return body


def _product(eid: str, name: str = "Schuh") -> dict[str, Any]:
    return {
        "external_id": eid,
        "name": name,
        "description": "Beschreibung des Produkts.",
        "categories": ["Schuhe", "Laufschuhe"],
        "price": "79.90",
        "currency": "EUR",
        "stock_status": "instock",
        "url": f"https://shop.example.com/{eid}",
    }


async def test_create_shop_returns_webhook_secret(integration_client: AsyncClient) -> None:
    body = await _new_shop(integration_client, "secret-test.example.com")
    assert "webhook_secret" in body
    assert len(body["webhook_secret"]) == 64


async def test_upsert_single_product(integration_client: AsyncClient) -> None:
    shop = await _new_shop(integration_client, "p1.example.com")
    api = shop["api_key"]
    resp = await integration_client.post(
        "/v1/products",
        json=_product("wc-1", "Trailrunner"),
        headers={"X-Api-Key": api},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["external_id"] == "wc-1"
    assert body["name"] == "Trailrunner"


async def test_upsert_is_idempotent_on_external_id(integration_client: AsyncClient) -> None:
    shop = await _new_shop(integration_client, "p2.example.com")
    api = shop["api_key"]
    first = await integration_client.post(
        "/v1/products", json=_product("wc-7", "v1"), headers={"X-Api-Key": api}
    )
    second = await integration_client.post(
        "/v1/products", json=_product("wc-7", "v2"), headers={"X-Api-Key": api}
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["name"] == "v2"


async def test_bulk_sync_returns_job_id_then_completes(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "p3.example.com")
    api = shop["api_key"]
    products = [_product(f"wc-{i}", f"Item {i}") for i in range(5)]
    start = await integration_client.post(
        "/v1/products/sync",
        json={"products": products},
        headers={"X-Api-Key": api},
    )
    assert start.status_code == 202, start.text
    job_id = start.json()["job_id"]
    assert start.json()["total"] == 5

    # Wait for the BackgroundTask to drain.
    for _ in range(50):
        status_resp = await integration_client.get(
            f"/v1/products/sync/{job_id}", headers={"X-Api-Key": api}
        )
        assert status_resp.status_code == 200
        if status_resp.json()["status"] == "complete":
            assert status_resp.json()["processed"] == 5
            assert status_resp.json()["failed"] == 0
            return
        await asyncio.sleep(0.1)
    pytest.fail("bulk sync did not complete within 5s")


async def test_sync_status_404_for_other_shops_job(integration_client: AsyncClient) -> None:
    shop_a = await _new_shop(integration_client, "p4-a.example.com")
    shop_b = await _new_shop(integration_client, "p4-b.example.com")
    start = await integration_client.post(
        "/v1/products/sync",
        json={"products": [_product("wc-x")]},
        headers={"X-Api-Key": shop_a["api_key"]},
    )
    job_id = start.json()["job_id"]
    leak = await integration_client.get(
        f"/v1/products/sync/{job_id}", headers={"X-Api-Key": shop_b["api_key"]}
    )
    assert leak.status_code == 404
