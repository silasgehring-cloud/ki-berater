"""Per-shop dynamic CORS middleware.

Replaces FastAPI's static `CORSMiddleware` with one that allows any origin
that maps to a registered shop. Allowed origins are derived from:

1. `Shop.domain` — used as `https://{domain}` and `http://{domain}` (dev)
2. `Shop.config['allowed_origins']` — explicit per-shop list

The set is cached on `app.state` for `cache_ttl_seconds` so the hot path
doesn't hit the DB. Tests reset the cache via `reset_cache(app)`.
"""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from sqlalchemy import select
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from backend.db.session import get_sessionmaker
from backend.models.shop import Shop

_CACHE_KEY = "cors_allowlist"
_EXPIRES_KEY = "cors_allowlist_expires_at"


def reset_cache(app: Starlette) -> None:
    """Clear the per-app CORS allowlist cache (used by tests)."""
    if hasattr(app.state, _CACHE_KEY):
        delattr(app.state, _CACHE_KEY)
    if hasattr(app.state, _EXPIRES_KEY):
        delattr(app.state, _EXPIRES_KEY)


class PerShopCORSMiddleware(BaseHTTPMiddleware):
    _ALLOW_HEADERS = "X-Api-Key, X-Webhook-Signature, Content-Type, Accept"
    _ALLOW_METHODS = "GET, POST, OPTIONS"
    _MAX_AGE = "600"

    def __init__(self, app: ASGIApp, cache_ttl_seconds: float = 60.0) -> None:
        super().__init__(app)
        self._cache_ttl = cache_ttl_seconds

    async def _refresh_allowlist(self, request: Request) -> set[str]:
        state = request.app.state
        now = time.monotonic()
        cached: set[str] | None = getattr(state, _CACHE_KEY, None)
        expires_at: float = getattr(state, _EXPIRES_KEY, 0.0)
        if cached is not None and now < expires_at:
            return cached

        factory = get_sessionmaker()
        async with factory() as session:
            stmt = select(Shop.domain, Shop.config)
            rows = (await session.execute(stmt)).all()

        allowed: set[str] = set()
        for domain, config in rows:
            allowed.add(f"https://{domain}")
            allowed.add(f"http://{domain}")
            extra = (config or {}).get("allowed_origins") or []
            if isinstance(extra, list):
                for o in extra:
                    if isinstance(o, str) and o.strip():
                        allowed.add(o.strip().rstrip("/"))

        setattr(state, _CACHE_KEY, allowed)
        setattr(state, _EXPIRES_KEY, now + self._cache_ttl)
        return allowed

    async def _is_allowed(self, request: Request, origin: str) -> bool:
        if not origin:
            return False
        allowed = await self._refresh_allowlist(request)
        return origin.rstrip("/") in allowed

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        origin = request.headers.get("origin", "")

        is_preflight = (
            request.method == "OPTIONS"
            and origin
            and "access-control-request-method" in request.headers
        )
        if is_preflight:
            if await self._is_allowed(request, origin):
                return Response(
                    status_code=204,
                    headers={
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Methods": self._ALLOW_METHODS,
                        "Access-Control-Allow-Headers": self._ALLOW_HEADERS,
                        "Access-Control-Max-Age": self._MAX_AGE,
                        "Access-Control-Allow-Credentials": "true",
                        "Vary": "Origin",
                    },
                )
            return Response(status_code=403)

        response = await call_next(request)
        if origin and await self._is_allowed(request, origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
        return response
