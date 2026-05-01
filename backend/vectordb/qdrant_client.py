"""Qdrant wrapper. ONE global collection `products`, `shop_id` payload filter.

All Qdrant access goes through this module — direct AsyncQdrantClient calls
elsewhere bypass tenant isolation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from qdrant_client import AsyncQdrantClient, models

if TYPE_CHECKING:
    pass

from backend.embeddings.embedder import EMBEDDING_DIM

COLLECTION = "products"


@dataclass(frozen=True)
class ProductHit:
    product_id: UUID
    score: float
    payload: dict[str, Any]


class VectorIndex:
    def __init__(self, client: AsyncQdrantClient) -> None:
        self._client = client

    @classmethod
    def from_url(cls, url: str) -> VectorIndex:
        # qdrant-client supports `:memory:` (local in-process) and HTTP URLs.
        client = (
            AsyncQdrantClient(":memory:") if url == ":memory:"
            else AsyncQdrantClient(url=url)
        )
        return cls(client)

    async def ensure_collection(self) -> None:
        existing = await self._client.get_collections()
        names = {c.name for c in existing.collections}
        if COLLECTION in names:
            return
        await self._client.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIM, distance=models.Distance.COSINE
            ),
        )
        # Index shop_id for cheap tenant filtering.
        await self._client.create_payload_index(
            collection_name=COLLECTION,
            field_name="shop_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

    async def upsert(
        self,
        *,
        shop_id: UUID,
        product_id: UUID,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        full_payload = {**payload, "shop_id": str(shop_id), "product_id": str(product_id)}
        await self._client.upsert(
            collection_name=COLLECTION,
            points=[
                models.PointStruct(
                    id=str(product_id),
                    vector=vector,
                    payload=full_payload,
                )
            ],
        )

    async def delete(self, *, shop_id: UUID, product_id: UUID) -> None:
        await self._client.delete(
            collection_name=COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="shop_id",
                            match=models.MatchValue(value=str(shop_id)),
                        ),
                        models.FieldCondition(
                            key="product_id",
                            match=models.MatchValue(value=str(product_id)),
                        ),
                    ]
                )
            ),
        )

    async def search(
        self,
        *,
        shop_id: UUID,
        vector: list[float],
        top_k: int = 5,
        in_stock_only: bool = True,
    ) -> list[ProductHit]:
        must: list[models.FieldCondition] = [
            models.FieldCondition(
                key="shop_id", match=models.MatchValue(value=str(shop_id))
            )
        ]
        if in_stock_only:
            must.append(
                models.FieldCondition(
                    key="stock_status", match=models.MatchValue(value="instock")
                )
            )
        result = await self._client.query_points(
            collection_name=COLLECTION,
            query=vector,
            query_filter=models.Filter(must=must),
            limit=top_k,
            with_payload=True,
        )
        hits: list[ProductHit] = []
        for point in result.points:
            payload = point.payload or {}
            pid = payload.get("product_id")
            if not pid:
                continue
            hits.append(
                ProductHit(
                    product_id=UUID(str(pid)),
                    score=point.score,
                    payload=payload,
                )
            )
        return hits

    async def close(self) -> None:
        await self._client.close()
