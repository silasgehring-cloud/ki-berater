"""Conversion attribution + 30-day overview aggregations + click events."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.tenant_query import tenant_select
from backend.models.conversation import Conversation
from backend.models.llm_usage import LLMUsage
from backend.models.message import Message
from backend.models.product import Product
from backend.models.product_click import ProductClick
from backend.models.shop import Shop
from backend.schemas.analytics import (
    AnalyticsOverview,
    AnalyticsPeriod,
    AttributionStats,
    ClickStats,
    ConversationStats,
    ConversionEvent,
    RevenueStats,
)

logger = structlog.get_logger("backend.analytics")

RecordResult = Literal["created", "already_recorded", "replaced", "not_found"]


async def _resolve_strict_attribution(
    db: AsyncSession,
    *,
    shop_id: UUID,
    conversation_id: UUID,
    line_item_external_ids: list[str],
) -> bool:
    """True iff at least one ordered line-item appears in the conversation's
    product references (the products the KI actually surfaced)."""
    if not line_item_external_ids:
        return False

    # 1. WC external_ids → internal Product UUIDs (tenant-scoped).
    pid_stmt = (
        tenant_select(Product, shop_id=shop_id)
        .where(Product.external_id.in_(line_item_external_ids))
    )
    ordered_pids = {p.id for p in (await db.execute(pid_stmt)).scalars().all()}
    if not ordered_pids:
        return False

    # 2. Sammle alle products_referenced der Conversation.
    msg_stmt = (
        tenant_select(Message, shop_id=shop_id)
        .where(Message.conversation_id == conversation_id)
        .where(Message.products_referenced.is_not(None))
    )
    referenced: set[UUID] = set()
    for m in (await db.execute(msg_stmt)).scalars().all():
        if m.products_referenced:
            referenced.update(m.products_referenced)

    return bool(ordered_pids & referenced)


async def record_conversion(
    db: AsyncSession,
    shop: Shop,
    conversation_id: UUID,
    payload: ConversionEvent,
) -> tuple[Conversation | None, RecordResult]:
    """Mark conversation as converted. Idempotent on (shop_id, order_id).

    Returns (conversation, status_code) where status_code is one of:
      - "created": newly marked
      - "already_recorded": same order_id already attributed; no-op
      - "replaced": different order_id was previously set; warning logged
      - "not_found": conversation does not exist for this shop (404)
    """
    stmt = tenant_select(Conversation, shop_id=shop.id).where(
        Conversation.id == conversation_id
    )
    convo = (await db.execute(stmt)).scalar_one_or_none()
    if convo is None:
        return None, "not_found"

    status: RecordResult = "created"
    if convo.converted and convo.order_id == payload.order_id:
        return convo, "already_recorded"

    if convo.converted and convo.order_id and convo.order_id != payload.order_id:
        logger.warning(
            "conversion.replace",
            shop_id=str(shop.id),
            conversation_id=str(conversation_id),
            old_order_id=convo.order_id,
            new_order_id=payload.order_id,
        )
        status = "replaced"

    is_strict = await _resolve_strict_attribution(
        db,
        shop_id=shop.id,
        conversation_id=conversation_id,
        line_item_external_ids=payload.line_item_external_ids,
    )

    convo.converted = True
    convo.converted_at = datetime.now(UTC)
    convo.order_id = payload.order_id
    convo.order_total_eur = payload.order_total_eur
    convo.order_currency = payload.currency.upper()
    convo.attribution_type = "strict" if is_strict else "cookie_only"
    await db.commit()
    await db.refresh(convo)
    return convo, status


async def record_click(
    db: AsyncSession,
    *,
    shop: Shop,
    conversation_id: UUID,
    product_id: UUID,
    message_id: UUID | None,
) -> ProductClick | None:
    """Record a click. Returns None when the conversation isn't ours."""
    convo_stmt = tenant_select(Conversation, shop_id=shop.id).where(
        Conversation.id == conversation_id
    )
    convo = (await db.execute(convo_stmt)).scalar_one_or_none()
    if convo is None:
        return None

    # Verify product belongs to the shop too — defends against forged product_ids.
    prod_stmt = tenant_select(Product, shop_id=shop.id).where(Product.id == product_id)
    if (await db.execute(prod_stmt)).scalar_one_or_none() is None:
        return None

    click = ProductClick(
        shop_id=shop.id,
        conversation_id=conversation_id,
        product_id=product_id,
        message_id=message_id,
    )
    db.add(click)
    await db.commit()
    await db.refresh(click)
    return click


async def get_overview(db: AsyncSession, shop: Shop, days: int = 30) -> AnalyticsOverview:
    days = max(1, min(days, 365))
    end = datetime.now(UTC)
    start = end - timedelta(days=days)

    total_convo = (
        await db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(
                Conversation.shop_id == shop.id,
                Conversation.started_at >= start,
                Conversation.started_at < end,
            )
        )
    ) or 0

    converted_count = (
        await db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(
                Conversation.shop_id == shop.id,
                Conversation.started_at >= start,
                Conversation.started_at < end,
                Conversation.converted.is_(True),
            )
        )
    ) or 0

    strict_count = (
        await db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(
                Conversation.shop_id == shop.id,
                Conversation.started_at >= start,
                Conversation.started_at < end,
                Conversation.attribution_type == "strict",
            )
        )
    ) or 0

    cookie_only_count = max(0, int(converted_count) - int(strict_count))

    revenue_sum: Decimal = (
        await db.scalar(
            select(func.coalesce(func.sum(Conversation.order_total_eur), 0))
            .where(
                Conversation.shop_id == shop.id,
                Conversation.started_at >= start,
                Conversation.started_at < end,
                Conversation.converted.is_(True),
            )
        )
    ) or Decimal("0")

    llm_cost: Decimal = (
        await db.scalar(
            select(func.coalesce(func.sum(LLMUsage.cost_eur), 0))
            .where(
                LLMUsage.shop_id == shop.id,
                LLMUsage.created_at >= start,
                LLMUsage.created_at < end,
            )
        )
    ) or Decimal("0")

    click_total = (
        await db.scalar(
            select(func.count())
            .select_from(ProductClick)
            .where(
                ProductClick.shop_id == shop.id,
                ProductClick.clicked_at >= start,
                ProductClick.clicked_at < end,
            )
        )
    ) or 0

    rate = round((converted_count / total_convo) * 100, 2) if total_convo else 0.0

    return AnalyticsOverview(
        period=AnalyticsPeriod(start=start.isoformat(), end=end.isoformat(), days=days),
        conversations=ConversationStats(
            total=int(total_convo),
            converted=int(converted_count),
            conversion_rate_percent=rate,
        ),
        revenue=RevenueStats(
            total_eur=Decimal(str(revenue_sum)),
            converted_orders=int(converted_count),
        ),
        clicks=ClickStats(total=int(click_total)),
        attribution=AttributionStats(
            strict=int(strict_count),
            cookie_only=int(cookie_only_count),
        ),
        llm_cost_eur=Decimal(str(llm_cost)),
    )
