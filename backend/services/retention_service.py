"""DSGVO-Retention: deletes conversations + messages + llm_usage older than
`settings.retention_days`. Runs hourly via an asyncio task started in main.py
lifespan.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import delete, func, select

from backend.core.config import settings
from backend.db.session import get_sessionmaker
from backend.models.conversation import Conversation
from backend.models.llm_usage import LLMUsage
from backend.models.message import Message

logger = structlog.get_logger("backend.retention")


async def purge_expired() -> dict[str, int]:
    """Delete records older than `settings.retention_days`. Returns counts."""
    cutoff = datetime.now(UTC) - timedelta(days=settings.retention_days)
    factory = get_sessionmaker()
    counts: dict[str, int] = {}
    async with factory() as session:
        # Order matters: messages -> conversations (FK), llm_usage independent.
        msg_count = await session.scalar(
            select(func.count()).select_from(Message).where(Message.created_at < cutoff)
        ) or 0
        await session.execute(delete(Message).where(Message.created_at < cutoff))

        convo_count = await session.scalar(
            select(func.count()).select_from(Conversation).where(Conversation.started_at < cutoff)
        ) or 0
        await session.execute(delete(Conversation).where(Conversation.started_at < cutoff))

        usage_count = await session.scalar(
            select(func.count()).select_from(LLMUsage).where(LLMUsage.created_at < cutoff)
        ) or 0
        await session.execute(delete(LLMUsage).where(LLMUsage.created_at < cutoff))

        await session.commit()
        counts = {
            "messages_deleted": msg_count,
            "conversations_deleted": convo_count,
            "llm_usage_deleted": usage_count,
        }

    logger.info("retention.purge", retention_days=settings.retention_days, **counts)
    return counts


async def retention_loop(interval_seconds: float = 3600.0) -> None:
    """Run `purge_expired` every `interval_seconds` until cancelled."""
    while True:
        try:
            await purge_expired()
        except Exception as exc:
            logger.exception("retention.failed", error=str(exc))
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break
