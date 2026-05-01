"""Bulk product sync via FastAPI BackgroundTasks.

Job state lives in-process (`_jobs` dict). This is fine for single-worker dev/CI.
Production multi-worker setups should switch to Redis or a `sync_jobs` table —
documented as a Sprint 1.4 follow-up.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.embeddings.embedder import Embedder
from backend.schemas.product import BulkSyncStatus, ProductIn
from backend.services.product_indexer import upsert_product
from backend.vectordb.qdrant_client import VectorIndex

logger = structlog.get_logger("backend.sync_service")

JobStatus = Literal["queued", "running", "complete", "failed"]


@dataclass
class _Job:
    job_id: UUID
    shop_id: UUID
    total: int
    processed: int = 0
    failed: int = 0
    status: JobStatus = "queued"
    error: str | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)


_jobs: dict[UUID, _Job] = {}


def register_job(shop_id: UUID, total: int) -> _Job:
    job = _Job(job_id=uuid4(), shop_id=shop_id, total=total)
    _jobs[job.job_id] = job
    return job


def get_job_status(job_id: UUID, shop_id: UUID) -> BulkSyncStatus | None:
    job = _jobs.get(job_id)
    if job is None or job.shop_id != shop_id:
        return None
    return BulkSyncStatus(
        job_id=job.job_id,
        status=job.status,
        total=job.total,
        processed=job.processed,
        failed=job.failed,
        error=job.error,
    )


async def run_bulk_sync(
    *,
    job_id: UUID,
    shop_id: UUID,
    products: list[ProductIn],
    sessionmaker: async_sessionmaker[AsyncSession],
    embedder: Embedder,
    vector_index: VectorIndex,
) -> None:
    job = _jobs[job_id]
    job.status = "running"
    logger.info("bulk_sync.start", job_id=str(job_id), total=job.total)

    for p in products:
        try:
            async with sessionmaker() as db:
                await upsert_product(
                    db,
                    shop_id=shop_id,
                    payload=p,
                    embedder=embedder,
                    vector_index=vector_index,
                )
                await db.commit()
            job.processed += 1
        except Exception as exc:
            job.failed += 1
            logger.warning(
                "bulk_sync.product_failed",
                job_id=str(job_id),
                external_id=p.external_id,
                error=str(exc),
            )

    job.status = "complete" if job.failed == 0 else "failed"
    if job.failed:
        job.error = f"{job.failed} of {job.total} products failed"
    logger.info(
        "bulk_sync.done",
        job_id=str(job_id),
        processed=job.processed,
        failed=job.failed,
    )
