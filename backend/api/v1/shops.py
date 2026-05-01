from fastapi import APIRouter, Depends, Request, status

from backend.api.deps import CurrentShop, DbSession, require_admin
from backend.api.rate_limit import limiter
from backend.schemas.shop import ShopCreate, ShopDataExport, ShopRead, ShopReadWithKey
from backend.services.export_service import export_shop_data
from backend.services.shop_service import create_shop

router = APIRouter(prefix="/v1/shops", tags=["shops"])


@router.post(
    "",
    response_model=ShopReadWithKey,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
@limiter.limit("5/minute")
async def create_shop_endpoint(
    request: Request,
    payload: ShopCreate,
    db: DbSession,
) -> ShopReadWithKey:
    shop, plain_key, webhook_secret = await create_shop(db, payload)
    return ShopReadWithKey(
        id=shop.id,
        domain=shop.domain,
        plan=shop.plan,
        api_key_prefix=shop.api_key_prefix,
        created_at=shop.created_at,
        api_key=plain_key,
        webhook_secret=webhook_secret,
    )


@router.get("/me", response_model=ShopRead)
async def get_my_shop(shop: CurrentShop) -> ShopRead:
    return ShopRead.model_validate(shop)


@router.get("/me/export", response_model=ShopDataExport)
async def export_my_shop(db: DbSession, shop: CurrentShop) -> ShopDataExport:
    """DSGVO Art. 15 — full data dump for the requesting shop."""
    return await export_shop_data(db, shop)
