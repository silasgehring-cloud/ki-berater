from httpx import AsyncClient


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_version(client: AsyncClient) -> None:
    response = await client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert "version" in body
    assert "environment" in body


async def test_ready_reports_components(integration_client: AsyncClient) -> None:
    """/ready against the test stack should be 'ready' — Postgres + Qdrant
    are up via fixtures. Redis isn't started in tests; it's expected to be
    'fail' or 'skipped' depending on REDIS_URL.
    """
    response = await integration_client.get("/ready")
    body = response.json()
    assert body["postgres"]["status"] == "ok"
    assert body["qdrant"]["status"] == "ok"
    # Redis may be unreachable in this sandbox — that's fine, just don't crash.
    assert body["redis"]["status"] in {"ok", "fail", "skipped"}
    # Status reflects whether any component failed.
    assert body["status"] in {"ready", "degraded"}
