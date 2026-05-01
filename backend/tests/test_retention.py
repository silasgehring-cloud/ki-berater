"""90-day retention service."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.conversation import Conversation
from backend.models.llm_usage import LLMUsage
from backend.models.message import Message
from backend.models.shop import Shop
from backend.services.retention_service import purge_expired

pytestmark = pytest.mark.integration


async def _make_shop(db: AsyncSession) -> Shop:
    from backend.core.security import generate_api_key, generate_webhook_secret

    _plain, prefix, hashed = generate_api_key()
    shop = Shop(
        domain="retention-test.example.com",
        plan="starter",
        api_key_hash=hashed,
        api_key_prefix=prefix,
        config={"webhook_secret": generate_webhook_secret()},
    )
    db.add(shop)
    await db.flush()
    return shop


async def test_purges_old_records(db: AsyncSession) -> None:
    shop = await _make_shop(db)
    old = datetime.now(UTC) - timedelta(days=settings.retention_days + 5)
    fresh = datetime.now(UTC) - timedelta(days=1)

    old_convo = Conversation(shop_id=shop.id, started_at=old)
    fresh_convo = Conversation(shop_id=shop.id, started_at=fresh)
    db.add_all([old_convo, fresh_convo])
    await db.flush()

    db.add_all([
        Message(shop_id=shop.id, conversation_id=old_convo.id, role="user",
                content="old", created_at=old),
        Message(shop_id=shop.id, conversation_id=fresh_convo.id, role="user",
                content="fresh", created_at=fresh),
    ])
    db.add_all([
        LLMUsage(shop_id=shop.id, conversation_id=fresh_convo.id, model="mock-1",
                 input_tokens=1, output_tokens=1, cached_tokens=0,
                 cost_eur=0, latency_ms=1, created_at=old),
        LLMUsage(shop_id=shop.id, conversation_id=fresh_convo.id, model="mock-1",
                 input_tokens=1, output_tokens=1, cached_tokens=0,
                 cost_eur=0, latency_ms=1, created_at=fresh),
    ])
    await db.commit()

    counts = await purge_expired()

    # Verify in a new session.
    from backend.db.session import get_sessionmaker

    async with get_sessionmaker()() as s2:
        remaining_convos = list((await s2.execute(select(Conversation))).scalars().all())
        remaining_msgs = list((await s2.execute(select(Message))).scalars().all())
        remaining_usage = list((await s2.execute(select(LLMUsage))).scalars().all())

    assert counts["messages_deleted"] >= 1
    assert counts["conversations_deleted"] >= 1
    assert counts["llm_usage_deleted"] >= 1
    assert all(c.id != old_convo.id for c in remaining_convos)
    assert any(c.id == fresh_convo.id for c in remaining_convos)
    assert all(m.content != "old" for m in remaining_msgs)
    assert any(m.content == "fresh" for m in remaining_msgs)
    assert len(remaining_usage) == 1


async def test_purge_is_idempotent_on_empty_db(db: AsyncSession) -> None:
    """No rows → no failure."""
    counts = await purge_expired()
    assert counts == {
        "messages_deleted": 0,
        "conversations_deleted": 0,
        "llm_usage_deleted": 0,
    }
