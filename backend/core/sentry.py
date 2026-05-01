"""Sentry-Integration. Off-by-default — initialize() ist no-op ohne `SENTRY_DSN`.

Bindet sich in FastAPI + asyncio + structlog ein und filtert die üblichen
Geräusch-Quellen raus (slowapi-RateLimitExceeded, ASGI-Disconnect).
"""
from __future__ import annotations

from typing import Any, cast

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from backend.core.config import settings

_NOISE_TYPES = ("RateLimitExceeded", "ClientDisconnect")


def _filter_noise(event: Any, hint: dict[str, Any]) -> Any:
    exc_info = hint.get("exc_info")
    if (
        exc_info
        and exc_info[0] is not None
        and exc_info[0].__name__ in _NOISE_TYPES
    ):
        return None
    return event


def initialize() -> bool:
    """Initialize the Sentry SDK if a DSN is configured. Returns whether init happened."""
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment or settings.environment,
        release=f"ki-berater@{settings.api_version}",
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,  # DSGVO — never send IPs/headers automatically
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            AsyncioIntegration(),
        ],
        before_send=cast(Any, _filter_noise),
    )
    return True
