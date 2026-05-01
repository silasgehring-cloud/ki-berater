from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from backend.api.deps import (
    CurrentShop,
    DbSession,
    EmbedderDep,
    SessionFactoryDep,
    VectorIndexDep,
)
from backend.schemas.product import (
    BulkSyncRequest,
    BulkSyncStarted,
    BulkSyncStatus,
    ProductIn,
    ProductRead,
)
from backend.services.product_indexer import upsert_product
from backend.services.sync_service import get_job_status, register_job, run_bulk_sync

router = APIRouter(prefix="/v1/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def upsert_one_product(
    payload: ProductIn,
    db: DbSession,
    shop: CurrentShop,
    embedder: EmbedderDep,
    vector_index: VectorIndexDep,
) -> ProductRead:
    product = await upsert_product(
        db,
        shop_id=shop.id,
        payload=payload,
        embedder=embedder,
        vector_index=vector_index,
    )
    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)


@router.post(
    "/sync",
    response_model=BulkSyncStarted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def bulk_sync(
    payload: BulkSyncRequest,
    background_tasks: BackgroundTasks,
    shop: CurrentShop,
    sessionmaker: SessionFactoryDep,
    embedder: EmbedderDep,
    vector_index: VectorIndexDep,
) -> BulkSyncStarted:
    job = register_job(shop.id, total=len(payload.products))
    products = payload.products
    background_tasks.add_task(
        run_bulk_sync,
        job_id=job.job_id,
        shop_id=shop.id,
        products=products,
        sessionmaker=sessionmaker,
        embedder=embedder,
        vector_index=vector_index,
    )
    return BulkSyncStarted(job_id=job.job_id, total=len(products))


@router.get("/sync/{job_id}", response_model=BulkSyncStatus)
async def get_sync_status(job_id: UUID, shop: CurrentShop) -> BulkSyncStatus:
    status_obj = get_job_status(job_id, shop.id)
    if status_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return status_obj
