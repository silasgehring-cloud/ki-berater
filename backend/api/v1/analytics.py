from fastapi import APIRouter, Query

from backend.api.deps import CurrentShop, DbSession
from backend.schemas.analytics import AnalyticsOverview
from backend.services.analytics_service import get_overview

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def overview(
    db: DbSession,
    shop: CurrentShop,
    days: int = Query(default=30, ge=1, le=365),
) -> AnalyticsOverview:
    return await get_overview(db, shop, days=days)
