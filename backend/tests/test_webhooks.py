"""WC webhook ingestion: HMAC verify, upsert + delete events."""
from __future__ import annotations

import json
from typing import Any

import pytest
from httpx import AsyncClient

from backend.core.security import sign_payload
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


def _signed(secret: str, body: dict[str, Any]) -> tuple[bytes, str]:
    raw = json.dumps(body).encode("utf-8")
    return raw, sign_payload(secret, raw)


def _make_payload(topic: str, eid: str = "wc-77", name: str = "Hut") -> dict[str, Any]:
    return {
        "topic": topic,
        "product": {
            "external_id": eid,
            "name": name,
            "description": "leichter Sommerhut",
            "categories": ["Hüte"],
            "price": "29.90",
            "currency": "EUR",
            "stock_status": "instock",
        },
    }


async def test_webhook_with_valid_signature_upserts(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "wh1.example.com")
    raw, sig = _signed(shop["webhook_secret"], _make_payload("product.created"))

    resp = await integration_client.post(
        "/v1/webhooks/products",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": shop["api_key"],
            "X-Webhook-Signature": sig,
        },
    )
    assert resp.status_code == 204, resp.text


async def test_webhook_rejects_missing_signature(integration_client: AsyncClient) -> None:
    shop = await _new_shop(integration_client, "wh2.example.com")
    resp = await integration_client.post(
        "/v1/webhooks/products",
        json=_make_payload("product.created"),
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.status_code == 401


async def test_webhook_rejects_tampered_body(integration_client: AsyncClient) -> None:
    shop = await _new_shop(integration_client, "wh3.example.com")
    raw, sig = _signed(shop["webhook_secret"], _make_payload("product.created"))
    # Tamper with the body but keep the original signature.
    tampered = raw.replace(b"Hut", b"BadActor")
    resp = await integration_client.post(
        "/v1/webhooks/products",
        content=tampered,
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": shop["api_key"],
            "X-Webhook-Signature": sig,
        },
    )
    assert resp.status_code == 401


async def test_webhook_rejects_signature_with_wrong_secret(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "wh4.example.com")
    raw, _ = _signed(shop["webhook_secret"], _make_payload("product.created"))
    bad_sig = sign_payload("wrong-secret", raw)
    resp = await integration_client.post(
        "/v1/webhooks/products",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": shop["api_key"],
            "X-Webhook-Signature": bad_sig,
        },
    )
    assert resp.status_code == 401


async def test_webhook_delete_topic_soft_deletes_product(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "wh5.example.com")
    api = shop["api_key"]

    # First upsert via the simpler /v1/products endpoint.
    upsert = await integration_client.post(
        "/v1/products",
        json={
            "external_id": "doomed",
            "name": "Soon Deleted",
            "description": "x",
            "categories": [],
            "stock_status": "instock",
        },
        headers={"X-Api-Key": api},
    )
    assert upsert.status_code == 201

    raw, sig = _signed(shop["webhook_secret"], _make_payload("product.deleted", "doomed", "x"))
    resp = await integration_client.post(
        "/v1/webhooks/products",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": api,
            "X-Webhook-Signature": sig,
        },
    )
    assert resp.status_code == 204
