"""WooCommerce → Backend webhook ingestion. HMAC-SHA256 signed by the WP plugin."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, status

from backend.api.deps import DbSession, EmbedderDep, VectorIndexDep, get_current_shop
from backend.core.security import verify_signature
from backend.schemas.product import WebhookPayload
from backend.services.product_indexer import soft_delete_product, upsert_product

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.post("/products", status_code=status.HTTP_204_NO_CONTENT)
async def woocommerce_product_webhook(
    request: Request,
    db: DbSession,
    embedder: EmbedderDep,
    vector_index: VectorIndexDep,
    x_webhook_signature: Annotated[str | None, Header(alias="X-Webhook-Signature")] = None,
) -> None:
    if not x_webhook_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing X-Webhook-Signature",
        )

    # Resolve shop via the same X-Api-Key flow.
    shop = await get_current_shop(
        db=db, x_api_key=request.headers.get("x-api-key")
    )

    secret = str(shop.config.get("webhook_secret") or "")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="shop has no webhook_secret configured",
        )

    raw_body = await request.body()
    if not verify_signature(secret, raw_body, x_webhook_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid webhook signature",
        )

    payload = WebhookPayload.model_validate_json(raw_body)

    if payload.topic == "product.deleted":
        await soft_delete_product(
            db,
            shop_id=shop.id,
            external_id=payload.product.external_id,
            vector_index=vector_index,
        )
    else:
        await upsert_product(
            db,
            shop_id=shop.id,
            payload=payload.product,
            embedder=embedder,
            vector_index=vector_index,
        )
    await db.commit()
