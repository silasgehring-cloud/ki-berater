"""Cross-tenant leak test — the contract this whole architecture exists to uphold.

Setup: two shops A and B. Shop A creates a conversation. Shop B tries to read it.
Expected: 404 (not 200). This must fail loudly if anyone bypasses tenant_select().
"""
import pytest
from httpx import AsyncClient

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


async def test_shop_b_cannot_read_shop_a_conversation(
    integration_client: AsyncClient,
) -> None:
    key_a = await _new_shop(integration_client, "shop-a.example.com")
    key_b = await _new_shop(integration_client, "shop-b.example.com")

    # Shop A creates a conversation.
    create = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "Insider info from shop A"},
        headers={"X-Api-Key": key_a},
    )
    assert create.status_code == 201
    convo_id = create.json()["conversation"]["id"]

    # Shop A can read it.
    own = await integration_client.get(
        f"/v1/conversations/{convo_id}",
        headers={"X-Api-Key": key_a},
    )
    assert own.status_code == 200

    # Shop B must NOT see it. 404 (indistinguishable from "doesn't exist").
    leak_attempt = await integration_client.get(
        f"/v1/conversations/{convo_id}",
        headers={"X-Api-Key": key_b},
    )
    assert leak_attempt.status_code == 404, (
        f"TENANT LEAK: shop B saw shop A's conversation {convo_id!r}"
    )


async def test_get_me_returns_only_own_shop(integration_client: AsyncClient) -> None:
    key_a = await _new_shop(integration_client, "shop-x.example.com")
    key_b = await _new_shop(integration_client, "shop-y.example.com")

    me_a = await integration_client.get("/v1/shops/me", headers={"X-Api-Key": key_a})
    me_b = await integration_client.get("/v1/shops/me", headers={"X-Api-Key": key_b})

    assert me_a.json()["domain"] == "shop-x.example.com"
    assert me_b.json()["domain"] == "shop-y.example.com"
    assert me_a.json()["id"] != me_b.json()["id"]
