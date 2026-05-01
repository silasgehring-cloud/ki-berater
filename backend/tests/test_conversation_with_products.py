"""Vector-augmented conversation: upserted products surface in the system prompt
and as `products_referenced` on the assistant message."""
from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.llm.providers.mock import MockProvider
from backend.llm.router import Router
from backend.main import app
from backend.models.message import Message
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


async def test_indexed_product_appears_in_system_prompt(
    integration_client: AsyncClient,
) -> None:
    """The mock provider records the system prompt sent to it; we assert the
    indexed product's name is present in that prompt."""
    from backend.api.deps import get_router

    mock = MockProvider(response="Probiere doch mal das Produkt!")
    custom_router = Router(
        providers={"only": mock},
        chains={"standard": ["only"], "complex": ["only"]},
    )
    app.dependency_overrides[get_router] = lambda: custom_router
    try:
        shop = await _new_shop(integration_client, "vec1.example.com")
        api = shop["api_key"]

        # Index a product so vector-search has something to find.
        await integration_client.post(
            "/v1/products",
            json={
                "external_id": "wc-shoe-1",
                "name": "Trail Master 3000",
                "description": "Robuster Trailrunner für unebene Strecken",
                "categories": ["Schuhe", "Trail"],
                "price": "129.00",
                "currency": "EUR",
                "stock_status": "instock",
                "url": "https://shop/trail-3000",
            },
            headers={"X-Api-Key": api},
        )

        msg = "Welcher Trail Master Trailrunner für unebene Strecken passt?"
        await integration_client.post(
            "/v1/conversations",
            json={"initial_message": msg},
            headers={"X-Api-Key": api},
        )

        # The mock recorded what the router actually sent.
        assert len(mock.calls) == 1
        system_prompt, _history = mock.calls[0]
        assert "Trail Master 3000" in system_prompt
    finally:
        app.dependency_overrides.pop(get_router, None)


async def test_assistant_message_records_products_referenced(
    integration_client: AsyncClient,
    db: AsyncSession,
) -> None:
    shop = await _new_shop(integration_client, "vec2.example.com")
    api = shop["api_key"]
    upsert = await integration_client.post(
        "/v1/products",
        json={
            "external_id": "wc-jacket",
            "name": "Regenjacke Storm",
            "description": "Wasserdichte Jacke",
            "categories": ["Jacken"],
            "stock_status": "instock",
        },
        headers={"X-Api-Key": api},
    )
    product_id = upsert.json()["id"]

    create = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "Wasserdichte Regenjacke Storm gesucht"},
        headers={"X-Api-Key": api},
    )
    assistant_id = create.json()["assistant_message"]["id"]

    stmt = select(Message).where(Message.id == assistant_id)
    rows = list((await db.execute(stmt)).scalars().all())
    assert len(rows) == 1
    refs = rows[0].products_referenced or []
    assert any(str(r) == product_id for r in refs)


async def test_no_products_indexed_falls_back_to_empty_context(
    integration_client: AsyncClient,
) -> None:
    from backend.api.deps import get_router

    mock = MockProvider(response="Keine Produkte verfügbar.")
    custom_router = Router(
        providers={"only": mock},
        chains={"standard": ["only"], "complex": ["only"]},
    )
    app.dependency_overrides[get_router] = lambda: custom_router
    try:
        shop = await _new_shop(integration_client, "vec3.example.com")
        api = shop["api_key"]
        resp = await integration_client.post(
            "/v1/conversations",
            json={"initial_message": "Hallo"},
            headers={"X-Api-Key": api},
        )
        assert resp.status_code == 201
        # Conversation still works even with empty product index.
        system_prompt, _history = mock.calls[0]
        assert "(keine Produktdaten" in system_prompt
    finally:
        app.dependency_overrides.pop(get_router, None)
