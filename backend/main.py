import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from backend.admin import admin_router
from backend.api import health as health_router
from backend.api.cors_middleware import PerShopCORSMiddleware
from backend.api.deps import get_vector_index
from backend.api.middleware import RequestContextMiddleware
from backend.api.rate_limit import limiter
from backend.api.security_headers import SecurityHeadersMiddleware
from backend.api.v1 import analytics as analytics_router
from backend.api.v1 import billing as billing_router
from backend.api.v1 import conversations as conversations_router
from backend.api.v1 import products as products_router
from backend.api.v1 import shops as shops_router
from backend.api.v1 import webhooks as webhooks_router
from backend.core.config import settings
from backend.core.logging import configure_logging, get_logger
from backend.core.sentry import initialize as initialize_sentry
from backend.db.session import dispose_engine
from backend.services.retention_service import retention_loop

configure_logging()
_sentry_active = initialize_sentry()
logger = get_logger(__name__)
if _sentry_active:
    logger.info("sentry.initialized", environment=settings.environment)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "startup",
        environment=settings.environment,
        version=settings.api_version,
    )
    vector_index = get_vector_index()
    await vector_index.ensure_collection()

    retention_task: asyncio.Task[None] | None = None
    if settings.retention_loop_enabled:
        retention_task = asyncio.create_task(retention_loop(), name="retention-loop")

    try:
        yield
    finally:
        if retention_task is not None:
            retention_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await retention_task
        await vector_index.close()
        await dispose_engine()
        logger.info("shutdown")


app = FastAPI(
    title="KI-Verkaufsberater Backend",
    version=settings.api_version,
    lifespan=lifespan,
)

# slowapi wiring
app.state.limiter = limiter


def _rate_limit_handler(_request: Request, exc: Exception) -> JSONResponse:
    detail = exc.detail if isinstance(exc, RateLimitExceeded) else str(exc)
    return JSONResponse(
        status_code=429,
        content={"detail": f"rate limit exceeded: {detail}"},
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
# Per-shop CORS: allowlist comes from registered Shop.domain + shop.config['allowed_origins'].
# Wildcard fallback (settings.cors_origins_list) is no longer applied.
app.add_middleware(PerShopCORSMiddleware)

app.include_router(shops_router.router)
app.include_router(conversations_router.router)
app.include_router(products_router.router)
app.include_router(webhooks_router.router)
app.include_router(billing_router.router)
app.include_router(billing_router.webhook_router)
app.include_router(analytics_router.router)
app.include_router(health_router.router)

# Admin UI: server-rendered Jinja2 templates + static assets at /admin/.
# Auth via cookie (token == ADMIN_API_KEY). 401 on /admin/* gets rewritten
# to a 302 to /admin/login by the handler below.
_ADMIN_STATIC = Path(__file__).resolve().parent / "admin" / "static"
app.mount("/admin/static", StaticFiles(directory=str(_ADMIN_STATIC)), name="admin-static")
app.include_router(admin_router)


@app.exception_handler(HTTPException)
async def _http_exc_handler(request: Request, exc: HTTPException) -> Response:
    """Turn 401s on /admin/* (non-HTMX, non-API) into a redirect to login."""
    if (
        exc.status_code == 401
        and request.url.path.startswith("/admin")
        and not request.url.path.startswith("/admin/login")
        and not request.headers.get("HX-Request")
    ):
        return RedirectResponse(
            url=f"/admin/login?next={request.url.path}",
            status_code=303,
        )
    # Default behaviour for everything else.
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness — always 200 if the process can answer."""
    return {"status": "ok"}


@app.get("/version")
async def version() -> dict[str, str]:
    return {
        "version": settings.api_version,
        "environment": settings.environment,
    }
