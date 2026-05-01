from fastapi import APIRouter, HTTPException, Request, status

from backend.api.deps import CurrentShop, DbSession
from backend.billing.service import (
    create_checkout_session,
    create_portal_session,
    handle_stripe_webhook,
    quota_status,
)
from backend.schemas.billing import (
    CheckoutCreate,
    CheckoutSessionRead,
    PortalSessionRead,
    QuotaStatus,
)

router = APIRouter(prefix="/v1/billing", tags=["billing"])


@router.post("/checkout", response_model=CheckoutSessionRead, status_code=status.HTTP_201_CREATED)
async def create_checkout(
    payload: CheckoutCreate,
    shop: CurrentShop,
) -> CheckoutSessionRead:
    try:
        url = await create_checkout_session(shop, plan=payload.plan)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CheckoutSessionRead(url=url)


@router.post("/portal", response_model=PortalSessionRead, status_code=status.HTTP_201_CREATED)
async def create_portal(shop: CurrentShop) -> PortalSessionRead:
    try:
        url = await create_portal_session(shop)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PortalSessionRead(url=url)


@router.get("/quota", response_model=QuotaStatus)
async def get_quota(db: DbSession, shop: CurrentShop) -> QuotaStatus:
    return QuotaStatus(**await quota_status(db, shop))


webhook_router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@webhook_router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, db: DbSession) -> dict[str, object]:
    sig = request.headers.get("Stripe-Signature", "")
    if not sig:
        raise HTTPException(status_code=400, detail="missing Stripe-Signature")
    raw = await request.body()
    try:
        return await handle_stripe_webhook(db, raw, sig)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"webhook verify failed: {exc}") from exc
