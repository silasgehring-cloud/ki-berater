"""Per-shop CORS allowlist."""
from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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


async def test_known_shop_origin_gets_acao_header(integration_client: AsyncClient) -> None:
    shop = await _new_shop(integration_client, "trusted.example.com")
    resp = await integration_client.get(
        "/health",
        headers={"Origin": "https://trusted.example.com"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "https://trusted.example.com"
    assert resp.headers.get("vary", "").lower().count("origin") >= 1
    assert shop["domain"] == "trusted.example.com"


async def test_unknown_origin_does_not_get_acao_header(
    integration_client: AsyncClient,
) -> None:
    await _new_shop(integration_client, "trusted.example.com")
    resp = await integration_client.get(
        "/health",
        headers={"Origin": "https://attacker.invalid"},
    )
    assert resp.status_code == 200
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}


async def test_preflight_for_known_origin_returns_204(integration_client: AsyncClient) -> None:
    await _new_shop(integration_client, "preflight.example.com")
    resp = await integration_client.request(
        "OPTIONS",
        "/v1/conversations",
        headers={
            "Origin": "https://preflight.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Api-Key, Content-Type",
        },
    )
    assert resp.status_code == 204
    assert resp.headers.get("access-control-allow-origin") == "https://preflight.example.com"
    assert "POST" in resp.headers.get("access-control-allow-methods", "")
    assert "X-Api-Key" in resp.headers.get("access-control-allow-headers", "")


async def test_preflight_for_unknown_origin_returns_403(integration_client: AsyncClient) -> None:
    await _new_shop(integration_client, "knownorigin.example.com")
    resp = await integration_client.request(
        "OPTIONS",
        "/v1/conversations",
        headers={
            "Origin": "https://evil.invalid",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 403


async def test_explicit_allowed_origins_in_shop_config_work(
    integration_client: AsyncClient,
    db: AsyncSession,
) -> None:
    shop = await _new_shop(integration_client, "shop-with-cdn.example.com")
    from sqlalchemy import update

    from backend.api import cors_middleware as cors_mw
    from backend.main import app
    from backend.models.shop import Shop

    await db.execute(
        update(Shop).where(Shop.id == shop["id"]).values(
            config={"webhook_secret": "x", "allowed_origins": ["https://cdn.example.com"]}
        )
    )
    await db.commit()
    cors_mw.reset_cache(app)

    resp = await integration_client.get(
        "/health",
        headers={"Origin": "https://cdn.example.com"},
    )
    assert resp.headers.get("access-control-allow-origin") == "https://cdn.example.com"
