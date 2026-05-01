from typing import Any

import pytest
from httpx import AsyncClient

from backend.tests.conftest import TEST_ADMIN_KEY

pytestmark = pytest.mark.integration


async def _create_shop(
    client: AsyncClient, domain: str = "shop.example.com"
) -> dict[str, Any]:
    resp = await client.post(
        "/v1/shops",
        json={"domain": domain, "plan": "starter"},
        headers={"X-Admin-Key": TEST_ADMIN_KEY},
    )
    assert resp.status_code == 201, resp.text
    body: dict[str, Any] = resp.json()
    return body


async def test_admin_can_create_shop(integration_client: AsyncClient) -> None:
    body = await _create_shop(integration_client)
    assert body["domain"] == "shop.example.com"
    assert body["plan"] == "starter"
    assert "api_key" in body
    assert body["api_key"].startswith(body["api_key_prefix"])
    assert "webhook_secret" in body
    assert len(body["webhook_secret"]) == 64


async def test_create_shop_requires_admin_key(integration_client: AsyncClient) -> None:
    resp = await integration_client.post(
        "/v1/shops",
        json={"domain": "x.example.com"},
    )
    assert resp.status_code == 401


async def test_create_shop_rejects_wrong_admin_key(integration_client: AsyncClient) -> None:
    resp = await integration_client.post(
        "/v1/shops",
        json={"domain": "x.example.com"},
        headers={"X-Admin-Key": "wrong"},
    )
    assert resp.status_code == 401


async def test_create_shop_validates_payload(integration_client: AsyncClient) -> None:
    resp = await integration_client.post(
        "/v1/shops",
        json={"domain": "ab", "plan": "platinum"},  # too short + invalid plan
        headers={"X-Admin-Key": TEST_ADMIN_KEY},
    )
    assert resp.status_code == 422


async def test_get_me_with_valid_api_key(integration_client: AsyncClient) -> None:
    created = await _create_shop(integration_client, "alpha.example.com")
    api_key = created["api_key"]
    resp = await integration_client.get("/v1/shops/me", headers={"X-Api-Key": api_key})
    assert resp.status_code == 200
    body = resp.json()
    assert body["domain"] == "alpha.example.com"
    assert body["id"] == created["id"]
    assert "api_key" not in body  # plain key never leaks back


async def test_get_me_rejects_missing_key(integration_client: AsyncClient) -> None:
    resp = await integration_client.get("/v1/shops/me")
    assert resp.status_code == 401


async def test_get_me_rejects_wrong_key(integration_client: AsyncClient) -> None:
    resp = await integration_client.get(
        "/v1/shops/me", headers={"X-Api-Key": "totally-bogus-key-string-here"}
    )
    assert resp.status_code == 401
