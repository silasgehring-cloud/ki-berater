"""DSGVO Art. 15 data export — bundle every tenant-scoped row for a shop."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.tenant_query import tenant_select
from backend.models.conversation import Conversation
from backend.models.llm_usage import LLMUsage
from backend.models.message import Message
from backend.models.product import Product
from backend.models.shop import Shop
from backend.schemas.shop import ShopDataExport

_JSON_NATIVE = (int, float, bool, str, list, dict)


def _row_to_dict(row: object, fields: list[str]) -> dict[str, object]:
    out: dict[str, object] = {}
    for f in fields:
        v = getattr(row, f, None)
        # Ensure JSON-serializable: UUID/datetime/Decimal -> str.
        out[f] = v if (v is None or isinstance(v, _JSON_NATIVE)) else str(v)
    return out


async def export_shop_data(db: AsyncSession, shop: Shop) -> ShopDataExport:
    products = list((
        await db.execute(tenant_select(Product, shop_id=shop.id))
    ).scalars().all())

    convos = list((
        await db.execute(tenant_select(Conversation, shop_id=shop.id))
    ).scalars().all())

    messages = list((
        await db.execute(tenant_select(Message, shop_id=shop.id))
    ).scalars().all())

    usage = list((
        await db.execute(tenant_select(LLMUsage, shop_id=shop.id))
    ).scalars().all())

    # Strip secrets from shop dump.
    shop_dict: dict[str, object] = {
        "id": str(shop.id),
        "domain": shop.domain,
        "plan": shop.plan,
        "config": {k: v for k, v in shop.config.items() if k != "webhook_secret"},
        "created_at": shop.created_at.isoformat(),
    }

    return ShopDataExport(
        shop=shop_dict,
        products=[
            _row_to_dict(p, ["id", "external_id", "name", "stock_status", "price",
                             "currency", "url", "created_at", "updated_at"])
            for p in products
        ],
        conversations=[
            _row_to_dict(c, ["id", "visitor_id", "started_at", "ended_at", "converted"])
            for c in convos
        ],
        messages=[
            _row_to_dict(m, ["id", "conversation_id", "role", "content", "created_at"])
            for m in messages
        ],
        llm_usage=[
            _row_to_dict(u, ["id", "conversation_id", "model", "input_tokens",
                             "output_tokens", "cached_tokens", "cost_eur",
                             "latency_ms", "created_at"])
            for u in usage
        ],
        exported_at=datetime.now(UTC),
    )


