"""Test fixtures.

Strategy:
- Unit tests (no DB fixture): run anywhere.
- Integration tests (`db` / `integration_client`): need Postgres.
  Resolution order:
    1. If `settings.database_url` is reachable → use it.
    2. Else, if `pgserver` is importable AND env `USE_EMBEDDED_POSTGRES != "0"`
       → spin up an embedded Postgres for the session.
    3. Else `pytest.skip(...)` integration tests.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import settings
from backend.main import app
from backend.models import Base

TEST_ADMIN_KEY = "test-admin-secret"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: requires a running Postgres at DATABASE_URL",
    )


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _try_connect(url: str) -> bool:
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


def _to_async_url(sync_url: str) -> str:
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return sync_url


@pytest.fixture(scope="session")
async def _postgres_engine() -> AsyncIterator[AsyncEngine]:
    db_url = settings.database_url

    if not await _try_connect(db_url):
        if os.environ.get("USE_EMBEDDED_POSTGRES", "1") == "0":
            pytest.skip(f"Postgres not reachable at {db_url} (embedded disabled)")
        try:
            import pgserver
        except ImportError:
            pytest.skip(f"Postgres not reachable at {db_url} and pgserver not installed")

        tmp = tempfile.mkdtemp(prefix="pgsrv_test_")
        srv = pgserver.get_server(tmp, cleanup_mode="stop")
        db_url = _to_async_url(srv.get_uri())

    engine = create_async_engine(db_url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db(
    _postgres_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(_postgres_engine, expire_on_commit=False, autoflush=False)
    # Any code path that grabs get_sessionmaker() directly (retention,
    # CORS middleware, /ready, sync_service) sees the test engine.
    import backend.api.cors_middleware as cors_mw_module
    import backend.api.health as health_module
    import backend.db.session as session_module
    import backend.services.retention_service as retention_module

    monkeypatch.setattr(session_module, "get_sessionmaker", lambda: factory)
    monkeypatch.setattr(cors_mw_module, "get_sessionmaker", lambda: factory)
    monkeypatch.setattr(retention_module, "get_sessionmaker", lambda: factory)
    monkeypatch.setattr(health_module, "get_sessionmaker", lambda: factory)

    async with factory() as session:
        await session.execute(
            text(
                "TRUNCATE shops, conversations, messages, llm_usage, products, "
                "product_clicks RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
        yield session


@pytest.fixture
async def mock_router() -> AsyncIterator[object]:
    """Mock LLM Router used by integration_client. Tests can swap providers
    via `app.dependency_overrides[get_router]` for fault-injection scenarios."""
    from backend.llm.providers.mock import MockProvider
    from backend.llm.router import Router

    mock = MockProvider(response="Mock-Antwort: gerne berate ich dich.")
    router = Router(
        providers={"gemini-flash": mock, "claude-haiku": mock,
                   "claude-sonnet": mock, "gemini-pro": mock},
        chains={
            "standard": ["gemini-flash", "claude-haiku"],
            "complex": ["claude-sonnet", "gemini-pro", "claude-haiku"],
        },
    )
    yield router


@pytest.fixture
async def mock_embedder() -> AsyncIterator[object]:
    from backend.embeddings.embedder import MockEmbedder
    yield MockEmbedder()


@pytest.fixture
async def vector_index(_postgres_engine: AsyncEngine) -> AsyncIterator[object]:
    """In-memory Qdrant per session — resets cleanly between test functions
    because each test truncates Postgres products and re-upserts as needed."""
    from backend.vectordb.qdrant_client import VectorIndex

    vi = VectorIndex.from_url(":memory:")
    await vi.ensure_collection()
    yield vi
    await vi.close()


@pytest.fixture
async def integration_client(
    db: AsyncSession,
    _postgres_engine: AsyncEngine,
    mock_router: object,
    mock_embedder: object,
    vector_index: object,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    from backend.api.deps import (
        db_session,
        get_embedder,
        get_router,
        get_session_factory,
        get_vector_index,
    )

    async def _override_db() -> AsyncIterator[AsyncSession]:
        yield db

    monkeypatch.setattr(settings, "admin_api_key", TEST_ADMIN_KEY)
    # Reset the rate-limiter so per-route limits don't bleed across tests
    # (e.g. POST /v1/shops is throttled to 5/min).
    from backend.api.rate_limit import limiter
    limiter.reset()
    app.dependency_overrides[db_session] = _override_db
    app.dependency_overrides[get_router] = lambda: mock_router
    app.dependency_overrides[get_embedder] = lambda: mock_embedder
    app.dependency_overrides[get_vector_index] = lambda: vector_index
    # Background-task sessionmaker uses the same test engine.
    from sqlalchemy.ext.asyncio import async_sessionmaker
    test_factory = async_sessionmaker(
        _postgres_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    app.dependency_overrides[get_session_factory] = lambda: test_factory
    # Module-level get_sessionmaker is already patched in the `db` fixture.

    # /ready calls get_vector_index() directly (not via FastAPI deps).
    import backend.api.health as health_module
    monkeypatch.setattr(health_module, "get_vector_index", lambda: vector_index)

    # Per-shop CORS caches its allowlist on app.state — reset between tests.
    import backend.api.cors_middleware as cors_mw_module
    cors_mw_module.reset_cache(app)

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        for dep in (db_session, get_router, get_embedder, get_vector_index, get_session_factory):
            app.dependency_overrides.pop(dep, None)
        cors_mw_module.reset_cache(app)
