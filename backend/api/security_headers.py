"""Security-headers middleware.

Adds defense-in-depth headers to every response. Values are conservative
defaults — most apply only to HTML responses but cost nothing to attach to
JSON, and admin-tooling that proxies our responses inherits them.

Tweak via constructor if a specific deployment needs to relax e.g. CSP
to allow an embedded admin iframe.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import ClassVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    _DEFAULTS: ClassVar[dict[str, str]] = {
        # No clickjacking — the API isn't meant to be iframe'd.
        "X-Frame-Options": "DENY",
        # Disable MIME sniffing on JSON responses.
        "X-Content-Type-Options": "nosniff",
        # Don't leak our paths to third-party origins via Referer.
        "Referrer-Policy": "strict-origin-when-cross-origin",
        # CSP suitable for a JSON API (no inline scripts, no embeds).
        "Content-Security-Policy": (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'none'"
        ),
        # Strict-Transport-Security only meaningful on HTTPS, but harmless on HTTP.
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        # Block most browser features by default.
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    def __init__(self, app: ASGIApp, overrides: dict[str, str] | None = None) -> None:
        super().__init__(app)
        self._headers = {**self._DEFAULTS, **(overrides or {})}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for k, v in self._headers.items():
            response.headers.setdefault(k, v)
        return response
