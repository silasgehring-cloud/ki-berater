"""Product upsert pipeline: text → embedding → Qdrant + Postgres."""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.embeddings.embedder import Embedder
from backend.models.product import Product
from backend.schemas.product import ProductIn
from backend.vectordb.qdrant_client import VectorIndex

logger = structlog.get_logger("backend.product_indexer")


def build_embedding_text(p: ProductIn) -> str:
    """Plan-decided composition: name + description + categories."""
    parts = [p.name]
    if p.description:
        parts.append(p.description)
    if p.categories:
        parts.append("Kategorien: " + ", ".join(p.categories))
    return "\n\n".join(parts)


async def upsert_product(
    db: AsyncSession,
    *,
    shop_id: UUID,
    payload: ProductIn,
    embedder: Embedder,
    vector_index: VectorIndex,
) -> Product:
    """Insert-or-update by (shop_id, external_id). Re-embeds and upserts in Qdrant."""
    stmt = select(Product).where(
        Product.shop_id == shop_id, Product.external_id == payload.external_id
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing is None:
        product = Product(shop_id=shop_id, external_id=payload.external_id)
        db.add(product)
    else:
        product = existing

    product.name = payload.name
    product.description = payload.description
    product.categories = list(payload.categories)
    product.price = payload.price
    product.currency = payload.currency
    product.stock_status = payload.stock_status
    product.url = payload.url
    product.image_url = payload.image_url
    product.sku = payload.sku
    product.deleted = False

    await db.flush()  # so product.id is assigned

    text = build_embedding_text(payload)
    vectors = await embedder.embed([text])
    if not vectors:
        raise RuntimeError("embedder returned no vector")

    await vector_index.upsert(
        shop_id=shop_id,
        product_id=product.id,
        vector=vectors[0],
        payload={
            "name": product.name,
            "stock_status": product.stock_status,
            "price": str(product.price) if product.price is not None else None,
            "currency": product.currency,
            "url": product.url,
            "image_url": product.image_url,
            "categories": product.categories,
            "external_id": product.external_id,
        },
    )
    return product


async def soft_delete_product(
    db: AsyncSession,
    *,
    shop_id: UUID,
    external_id: str,
    vector_index: VectorIndex,
) -> bool:
    stmt = select(Product).where(
        Product.shop_id == shop_id, Product.external_id == external_id
    )
    product = (await db.execute(stmt)).scalar_one_or_none()
    if product is None:
        return False
    product.deleted = True
    product.stock_status = "outofstock"
    await db.flush()
    await vector_index.delete(shop_id=shop_id, product_id=product.id)
    return True
