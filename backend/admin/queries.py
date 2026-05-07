"""Admin-level read queries — cross-tenant aggregations.

The owner-admin sees ALL shops; per-shop tenant scoping does NOT apply
here. Keep this module read-only; mutations go through the regular
service layer (so plan logic, validation, audit etc. stay consistent).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.conversation import Conversation
from backend.models.llm_usage import LLMUsage
from backend.models.message import Message
from backend.models.product import Product
from backend.models.shop import Shop


class GlobalOverview(TypedDict):
    shop_count: int
    active_subscription_count: int
    conversations_30d: int
    converted_30d: int
    conversion_rate_30d: float
    revenue_30d_eur: Decimal
    llm_cost_30d_eur: Decimal


class ShopRow(TypedDict):
    id: UUID
    domain: str
    plan: str
    subscription_status: str
    api_key_prefix: str
    products: int
    conversations_30d: int
    revenue_30d_eur: Decimal
    created_at: datetime


class ConversationRow(TypedDict):
    id: UUID
    started_at: datetime
    shop_domain: str
    shop_id: UUID
    converted: bool
    attribution_type: str | None
    order_total_eur: Decimal | None
    message_count: int


def _last_30_days() -> tuple[datetime, datetime]:
    end = datetime.now(UTC)
    start = end - timedelta(days=30)
    return start, end


async def fetch_global_overview(db: AsyncSession) -> GlobalOverview:
    start, end = _last_30_days()

    shop_count = (await db.scalar(select(func.count()).select_from(Shop))) or 0
    active = (
        await db.scalar(
            select(func.count())
            .select_from(Shop)
            .where(Shop.subscription_status == "active")
        )
    ) or 0

    convo_total = (
        await db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.started_at >= start, Conversation.started_at < end)
        )
    ) or 0
    converted = (
        await db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(
                Conversation.started_at >= start,
                Conversation.started_at < end,
                Conversation.converted.is_(True),
            )
        )
    ) or 0
    revenue = (
        await db.scalar(
            select(func.coalesce(func.sum(Conversation.order_total_eur), 0))
            .where(
                Conversation.started_at >= start,
                Conversation.started_at < end,
                Conversation.converted.is_(True),
            )
        )
    ) or Decimal("0")
    llm_cost = (
        await db.scalar(
            select(func.coalesce(func.sum(LLMUsage.cost_eur), 0))
            .where(LLMUsage.created_at >= start, LLMUsage.created_at < end)
        )
    ) or Decimal("0")

    rate = round((converted / convo_total) * 100, 2) if convo_total else 0.0

    return GlobalOverview(
        shop_count=int(shop_count),
        active_subscription_count=int(active),
        conversations_30d=int(convo_total),
        converted_30d=int(converted),
        conversion_rate_30d=rate,
        revenue_30d_eur=Decimal(str(revenue)),
        llm_cost_30d_eur=Decimal(str(llm_cost)),
    )


async def fetch_shop_rows(db: AsyncSession) -> list[ShopRow]:
    """One row per shop with counts joined in. Done as separate scalars
    rather than a single mega-join for clarity; shop count stays small."""
    start, end = _last_30_days()

    shops = (
        (await db.execute(select(Shop).order_by(desc(Shop.created_at)))).scalars().all()
    )

    rows: list[ShopRow] = []
    for s in shops:
        products = (
            await db.scalar(
                select(func.count()).select_from(Product).where(Product.shop_id == s.id)
            )
        ) or 0
        convos = (
            await db.scalar(
                select(func.count())
                .select_from(Conversation)
                .where(
                    Conversation.shop_id == s.id,
                    Conversation.started_at >= start,
                    Conversation.started_at < end,
                )
            )
        ) or 0
        revenue = (
            await db.scalar(
                select(func.coalesce(func.sum(Conversation.order_total_eur), 0))
                .where(
                    Conversation.shop_id == s.id,
                    Conversation.started_at >= start,
                    Conversation.started_at < end,
                    Conversation.converted.is_(True),
                )
            )
        ) or Decimal("0")
        rows.append(
            ShopRow(
                id=s.id,
                domain=s.domain,
                plan=s.plan,
                subscription_status=s.subscription_status,
                api_key_prefix=s.api_key_prefix,
                products=int(products),
                conversations_30d=int(convos),
                revenue_30d_eur=Decimal(str(revenue)),
                created_at=s.created_at,
            )
        )
    return rows


async def fetch_shop(db: AsyncSession, shop_id: UUID) -> Shop | None:
    return (
        await db.execute(select(Shop).where(Shop.id == shop_id))
    ).scalar_one_or_none()


async def fetch_conversations(
    db: AsyncSession,
    shop_id: UUID | None = None,
    converted: bool | None = None,
    limit: int = 100,
) -> list[ConversationRow]:
    stmt = (
        select(
            Conversation.id,
            Conversation.started_at,
            Conversation.shop_id,
            Conversation.converted,
            Conversation.attribution_type,
            Conversation.order_total_eur,
            Shop.domain,
        )
        .join(Shop, Shop.id == Conversation.shop_id)
        .order_by(desc(Conversation.started_at))
        .limit(limit)
    )
    if shop_id is not None:
        stmt = stmt.where(Conversation.shop_id == shop_id)
    if converted is not None:
        stmt = stmt.where(Conversation.converted.is_(converted))

    result = await db.execute(stmt)
    rows: list[ConversationRow] = []
    for r in result.all():
        msg_count = (
            await db.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.conversation_id == r.id)
            )
        ) or 0
        rows.append(
            ConversationRow(
                id=r.id,
                started_at=r.started_at,
                shop_domain=r.domain,
                shop_id=r.shop_id,
                converted=bool(r.converted),
                attribution_type=r.attribution_type,
                order_total_eur=r.order_total_eur,
                message_count=int(msg_count),
            )
        )
    return rows


async def fetch_conversation_with_messages(
    db: AsyncSession, conversation_id: UUID
) -> tuple[Conversation, Shop, list[Message]] | None:
    convo = (
        await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
    ).scalar_one_or_none()
    if convo is None:
        return None
    shop = (
        await db.execute(select(Shop).where(Shop.id == convo.shop_id))
    ).scalar_one_or_none()
    if shop is None:
        return None
    messages = (
        (
            await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
        )
        .scalars()
        .all()
    )
    return convo, shop, list(messages)


async def fetch_recent_conversations(
    db: AsyncSession, shop_id: UUID, limit: int = 10
) -> list[ConversationRow]:
    return await fetch_conversations(db, shop_id=shop_id, limit=limit)
