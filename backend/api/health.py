"""Liveness vs. readiness.

`/health` returns 200 unconditionally — it answers "is the process alive".
Used by `docker-compose` healthcheck and orchestrator restart loops.

`/ready` pings every backing service and returns 503 if any is down. Used by
load-balancer / k8s readiness probes — under-pressure pods are de-routed
without being killed.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Literal, cast

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text as sql_text

from backend.api.deps import get_vector_index
from backend.db.session import get_sessionmaker

router = APIRouter(tags=["health"])

_PROBE_TIMEOUT = 2.0


class ComponentHealth(BaseModel):
    status: Literal["ok", "fail", "skipped"]
    detail: str | None = None


class ReadyReport(BaseModel):
    status: Literal["ready", "degraded"]
    postgres: ComponentHealth
    redis: ComponentHealth
    qdrant: ComponentHealth


async def _probe_postgres() -> ComponentHealth:
    try:
        factory = get_sessionmaker()
        async with factory() as session:
            await asyncio.wait_for(
                session.execute(sql_text("SELECT 1")), timeout=_PROBE_TIMEOUT
            )
        return ComponentHealth(status="ok")
    except Exception as exc:
        return ComponentHealth(status="fail", detail=str(exc)[:200])


async def _probe_redis() -> ComponentHealth:
    from backend.core.config import settings

    if not settings.redis_url:
        return ComponentHealth(status="skipped", detail="REDIS_URL not set")
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url, socket_timeout=_PROBE_TIMEOUT)
        try:
            ping_coro = cast(Awaitable[bool], client.ping())
            pong = await asyncio.wait_for(ping_coro, timeout=_PROBE_TIMEOUT)
            if pong:
                return ComponentHealth(status="ok")
            return ComponentHealth(status="fail", detail="ping returned falsy")
        finally:
            await client.aclose()
    except Exception as exc:
        return ComponentHealth(status="fail", detail=str(exc)[:200])


async def _probe_qdrant() -> ComponentHealth:
    try:
        vi = get_vector_index()
        await asyncio.wait_for(vi.ensure_collection(), timeout=_PROBE_TIMEOUT)
        return ComponentHealth(status="ok")
    except Exception as exc:
        return ComponentHealth(status="fail", detail=str(exc)[:200])


@router.get("/ready", response_model=ReadyReport)
async def ready(response: Response) -> ReadyReport:
    pg, rd, qd = await asyncio.gather(
        _probe_postgres(), _probe_redis(), _probe_qdrant()
    )
    fail = any(c.status == "fail" for c in (pg, rd, qd))
    if fail:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyReport(
        status="degraded" if fail else "ready",
        postgres=pg,
        redis=rd,
        qdrant=qd,
    )
