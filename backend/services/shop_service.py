from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import (
    generate_api_key,
    generate_webhook_secret,
    verify_api_key,
)
from backend.models.shop import Shop
from backend.schemas.shop import ShopCreate


async def create_shop(db: AsyncSession, payload: ShopCreate) -> tuple[Shop, str, str]:
    """Create a Shop and return it together with the plain API key + webhook
    secret (both shown exactly once at creation)."""
    plain, prefix, hashed = generate_api_key()
    webhook_secret = generate_webhook_secret()
    config = dict(payload.config)
    config["webhook_secret"] = webhook_secret
    shop = Shop(
        domain=payload.domain,
        plan=payload.plan,
        config=config,
        api_key_hash=hashed,
        api_key_prefix=prefix,
    )
    db.add(shop)
    await db.commit()
    await db.refresh(shop)
    return shop, plain, webhook_secret


async def find_shop_by_api_key(db: AsyncSession, plain_api_key: str) -> Shop | None:
    """Look up a shop by its plain API key.

    We narrow candidates by `api_key_prefix` (indexed) before performing the
    expensive Argon2 verification.
    """
    if len(plain_api_key) < 8:
        return None
    prefix = plain_api_key[:8]
    stmt = select(Shop).where(Shop.api_key_prefix == prefix)
    result = await db.execute(stmt)
    candidates = result.scalars().all()
    for shop in candidates:
        if verify_api_key(plain_api_key, shop.api_key_hash):
            return shop
    return None
