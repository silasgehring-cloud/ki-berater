"""Billing service — checkout, portal, webhook handling, period-usage counting."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.billing.plans import all_plans, get_plan
from backend.billing.stripe_client import get_stripe_client
from backend.core.config import settings
from backend.models.conversation import Conversation
from backend.models.shop import Shop

logger = structlog.get_logger("backend.billing")

_FALLBACK_PERIOD_DAYS = 30


async def create_checkout_session(shop: Shop, plan: str) -> str:
    """Return the Stripe Checkout URL the shop owner should visit to subscribe."""
    plan_obj = get_plan(plan)
    if not plan_obj.stripe_price_id:
        raise ValueError(f"plan {plan!r} has no stripe_price_id configured")

    client = get_stripe_client()
    kwargs: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": plan_obj.stripe_price_id, "quantity": 1}],
        "success_url": settings.stripe_success_url,
        "cancel_url": settings.stripe_cancel_url,
        "client_reference_id": str(shop.id),
        "metadata": {"shop_id": str(shop.id), "plan": plan},
    }
    if shop.stripe_customer_id:
        kwargs["customer"] = shop.stripe_customer_id
    else:
        kwargs["customer_email"] = f"billing@{shop.domain}"

    session = client.create_checkout_session(**kwargs)
    return str(session.url)


async def create_portal_session(shop: Shop) -> str:
    """Return the Stripe Customer Portal URL for self-service plan changes."""
    if not shop.stripe_customer_id:
        raise ValueError("shop has no stripe_customer_id; finish checkout first")
    client = get_stripe_client()
    session = client.create_billing_portal_session(
        customer=shop.stripe_customer_id,
        return_url=settings.stripe_success_url,
    )
    return str(session.url)


def _get_current_period(shop: Shop) -> tuple[datetime, datetime]:
    """Return (period_start, period_end) for usage counting.

    With an active Stripe subscription, periods come from `shop.current_period_*`.
    Without one, fall back to a rolling 30-day window so the starter plan still
    enforces something rather than allowing unlimited free usage.
    """
    if shop.current_period_start and shop.current_period_end:
        return (shop.current_period_start, shop.current_period_end)
    now = datetime.now(UTC)
    return (now - timedelta(days=_FALLBACK_PERIOD_DAYS), now)


async def count_period_usage(db: AsyncSession, shop: Shop) -> int:
    """Number of conversations in the current billing period."""
    period_start, period_end = _get_current_period(shop)
    stmt = (
        select(func.count())
        .select_from(Conversation)
        .where(
            Conversation.shop_id == shop.id,
            Conversation.started_at >= period_start,
            Conversation.started_at < period_end,
        )
    )
    return int(await db.scalar(stmt) or 0)


async def is_within_quota(db: AsyncSession, shop: Shop) -> bool:
    """True if the shop can still create new conversations this period."""
    plan = get_plan(shop.plan)
    if plan.monthly_conversations is None:
        return True  # enterprise / unlimited
    used = await count_period_usage(db, shop)
    return used < plan.monthly_conversations


async def quota_status(db: AsyncSession, shop: Shop) -> dict[str, Any]:
    plan = get_plan(shop.plan)
    used = await count_period_usage(db, shop)
    limit = plan.monthly_conversations
    period_start, period_end = _get_current_period(shop)
    return {
        "plan": plan.plan,
        "monthly_eur": plan.monthly_eur,
        "monthly_conversations": limit,
        "used_in_period": used,
        "remaining": (limit - used) if limit is not None else None,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "subscription_status": shop.subscription_status,
    }


def _resolve_plan_from_price_id(price_id: str | None) -> str | None:
    if not price_id:
        return None
    for plan_id, p in all_plans().items():
        if p.stripe_price_id and p.stripe_price_id == price_id:
            return plan_id
    return None


async def handle_stripe_webhook(
    db: AsyncSession, payload: bytes, sig_header: str
) -> dict[str, Any]:
    """Verify signature, update shop on subscription events. Returns a small status dict."""
    if not settings.stripe_webhook_secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET not configured")
    client = get_stripe_client()
    event = client.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    event_type = event["type"] if isinstance(event, dict) else event.type
    obj: Any = event["data"]["object"] if isinstance(event, dict) else event.data.object

    handled = False
    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, obj)
        handled = True
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
    }:
        await _handle_subscription_changed(db, obj)
        handled = True
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, obj)
        handled = True

    logger.info("billing.webhook", type=event_type, handled=handled)
    return {"handled": handled, "event_type": event_type}


def _g(o: Any, key: str, default: Any = None) -> Any:
    """Stripe SDK objects support both attribute and item access; tests pass dicts."""
    if isinstance(o, dict):
        return o.get(key, default)
    return getattr(o, key, default)


async def _handle_checkout_completed(db: AsyncSession, session: Any) -> None:
    shop_id_str = _g(_g(session, "metadata") or {}, "shop_id") or _g(session, "client_reference_id")
    if not shop_id_str:
        return
    shop = await db.get(Shop, UUID(str(shop_id_str)))
    if shop is None:
        return
    customer_id = _g(session, "customer")
    sub_id = _g(session, "subscription")
    if customer_id:
        shop.stripe_customer_id = str(customer_id)
    if sub_id:
        shop.stripe_subscription_id = str(sub_id)
    shop.subscription_status = "active"
    await db.commit()


def _epoch_to_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=UTC)


async def _handle_subscription_changed(db: AsyncSession, sub: Any) -> None:
    sub_id = _g(sub, "id")
    if not sub_id:
        return
    stmt = select(Shop).where(Shop.stripe_subscription_id == str(sub_id))
    shop = (await db.execute(stmt)).scalar_one_or_none()
    if shop is None:
        return
    shop.subscription_status = str(_g(sub, "status") or "active")
    shop.current_period_start = _epoch_to_dt(_g(sub, "current_period_start"))
    shop.current_period_end = _epoch_to_dt(_g(sub, "current_period_end"))

    items = _g(sub, "items") or {}
    data = _g(items, "data") or []
    if data:
        first = data[0]
        price = _g(first, "price") or {}
        price_id = _g(price, "id")
        plan_id = _resolve_plan_from_price_id(str(price_id)) if price_id else None
        if plan_id:
            shop.plan = plan_id
    await db.commit()


async def _handle_subscription_deleted(db: AsyncSession, sub: Any) -> None:
    sub_id = _g(sub, "id")
    if not sub_id:
        return
    stmt = select(Shop).where(Shop.stripe_subscription_id == str(sub_id))
    shop = (await db.execute(stmt)).scalar_one_or_none()
    if shop is None:
        return
    shop.subscription_status = "canceled"
    await db.commit()
