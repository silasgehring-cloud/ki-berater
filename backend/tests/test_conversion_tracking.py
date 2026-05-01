"""Conversion tracking endpoint — idempotency, tenant isolation, validation."""
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


async def _start_convo(client: AsyncClient, api_key: str) -> str:
    resp = await client.post(
        "/v1/conversations",
        json={"initial_message": "Hi"},
        headers={"X-Api-Key": api_key},
    )
    assert resp.status_code == 201
    return str(resp.json()["conversation"]["id"])


async def test_conversion_marks_conversation_converted(integration_client: AsyncClient) -> None:
    shop = await _new_shop(integration_client, "conv-1.example.com")
    cid = await _start_convo(integration_client, shop["api_key"])

    resp = await integration_client.post(
        f"/v1/conversations/{cid}/conversion",
        json={"order_id": "wc-order-42", "order_total_eur": "129.90", "currency": "EUR"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["converted"] is True
    assert body["order_id"] == "wc-order-42"
    assert body["order_total_eur"] == "129.90"
    assert body["order_currency"] == "EUR"
    assert body["converted_at"] is not None


async def test_conversion_is_idempotent_on_same_order(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "conv-idempotent.example.com")
    cid = await _start_convo(integration_client, shop["api_key"])

    payload = {"order_id": "wc-1", "order_total_eur": "50.00", "currency": "EUR"}
    first = await integration_client.post(
        f"/v1/conversations/{cid}/conversion",
        json=payload,
        headers={"X-Api-Key": shop["api_key"]},
    )
    second = await integration_client.post(
        f"/v1/conversations/{cid}/conversion",
        json=payload,
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["converted_at"] == second.json()["converted_at"]


async def test_conversion_replaces_on_different_order_id(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "conv-replace.example.com")
    cid = await _start_convo(integration_client, shop["api_key"])

    await integration_client.post(
        f"/v1/conversations/{cid}/conversion",
        json={"order_id": "wc-old", "order_total_eur": "10.00", "currency": "EUR"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    second = await integration_client.post(
        f"/v1/conversations/{cid}/conversion",
        json={"order_id": "wc-new", "order_total_eur": "99.00", "currency": "EUR"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert second.status_code == 200
    assert second.json()["order_id"] == "wc-new"
    assert second.json()["order_total_eur"] == "99.00"


async def test_conversion_404_for_other_shops_conversation(
    integration_client: AsyncClient,
) -> None:
    shop_a = await _new_shop(integration_client, "conv-a.example.com")
    shop_b = await _new_shop(integration_client, "conv-b.example.com")
    cid_a = await _start_convo(integration_client, shop_a["api_key"])

    leak = await integration_client.post(
        f"/v1/conversations/{cid_a}/conversion",
        json={"order_id": "x", "order_total_eur": "1.00", "currency": "EUR"},
        headers={"X-Api-Key": shop_b["api_key"]},
    )
    assert leak.status_code == 404


async def test_conversion_404_for_unknown_conversation_id(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "conv-unknown.example.com")
    resp = await integration_client.post(
        "/v1/conversations/00000000-0000-0000-0000-000000000000/conversion",
        json={"order_id": "x", "order_total_eur": "1.00", "currency": "EUR"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.status_code == 404


async def test_conversion_validation_rejects_negative_total(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "conv-validate.example.com")
    cid = await _start_convo(integration_client, shop["api_key"])
    resp = await integration_client.post(
        f"/v1/conversations/{cid}/conversion",
        json={"order_id": "x", "order_total_eur": "-1.00", "currency": "EUR"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.status_code == 422


async def test_conversion_validation_rejects_currency_length(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "conv-cur.example.com")
    cid = await _start_convo(integration_client, shop["api_key"])
    resp = await integration_client.post(
        f"/v1/conversations/{cid}/conversion",
        json={"order_id": "x", "order_total_eur": "1.00", "currency": "EURO"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.status_code == 422
