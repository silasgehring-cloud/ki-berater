"""End-to-end tests for /v1/conversations endpoints (Sprint 1.2).

Uses MockProvider for deterministic LLM behavior. Real providers are tested
against live keys in CI, not here.
"""
from __future__ import annotations

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


async def test_create_conversation_returns_user_and_assistant_messages(
    integration_client: AsyncClient,
) -> None:
    api_key = await _new_shop(integration_client, "shop1.example.com")
    resp = await integration_client.post(
        "/v1/conversations",
        json={"visitor_id": "v-123", "initial_message": "Hallo, ich brauche Beratung"},
        headers={"X-Api-Key": api_key},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["conversation"]["visitor_id"] == "v-123"
    assert body["user_message"]["role"] == "user"
    assert body["user_message"]["content"] == "Hallo, ich brauche Beratung"
    assert body["assistant_message"]["role"] == "assistant"
    assert len(body["assistant_message"]["content"]) > 0


async def test_get_conversation_after_creation(integration_client: AsyncClient) -> None:
    api_key = await _new_shop(integration_client, "shop2.example.com")
    create = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "Hi"},
        headers={"X-Api-Key": api_key},
    )
    convo_id = create.json()["conversation"]["id"]
    fetch = await integration_client.get(
        f"/v1/conversations/{convo_id}", headers={"X-Api-Key": api_key}
    )
    assert fetch.status_code == 200
    assert fetch.json()["id"] == convo_id


async def test_create_conversation_validates_payload(integration_client: AsyncClient) -> None:
    api_key = await _new_shop(integration_client, "shop3.example.com")
    resp = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": ""},
        headers={"X-Api-Key": api_key},
    )
    assert resp.status_code == 422


async def test_create_conversation_requires_auth(integration_client: AsyncClient) -> None:
    resp = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "hi"},
    )
    assert resp.status_code == 401


async def test_fetch_unknown_conversation_returns_404(integration_client: AsyncClient) -> None:
    api_key = await _new_shop(integration_client, "shop4.example.com")
    resp = await integration_client.get(
        "/v1/conversations/00000000-0000-0000-0000-000000000000",
        headers={"X-Api-Key": api_key},
    )
    assert resp.status_code == 404


async def test_append_message_returns_exchange(integration_client: AsyncClient) -> None:
    api_key = await _new_shop(integration_client, "shop5.example.com")
    create = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "Erste Nachricht"},
        headers={"X-Api-Key": api_key},
    )
    convo_id = create.json()["conversation"]["id"]

    follow_up = await integration_client.post(
        f"/v1/conversations/{convo_id}/messages",
        json={"content": "Zweite Nachricht — wie passt sie zur ersten?"},
        headers={"X-Api-Key": api_key},
    )
    assert follow_up.status_code == 201, follow_up.text
    body = follow_up.json()
    assert body["user_message"]["role"] == "user"
    assert body["assistant_message"]["role"] == "assistant"


async def test_append_to_unknown_conversation_returns_404(
    integration_client: AsyncClient,
) -> None:
    api_key = await _new_shop(integration_client, "shop6.example.com")
    resp = await integration_client.post(
        "/v1/conversations/00000000-0000-0000-0000-000000000000/messages",
        json={"content": "noop"},
        headers={"X-Api-Key": api_key},
    )
    assert resp.status_code == 404
