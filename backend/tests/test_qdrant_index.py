"""Qdrant in-memory: upsert, search, tenant filter, delete."""
from uuid import uuid4

import pytest

from backend.embeddings.embedder import MockEmbedder
from backend.vectordb.qdrant_client import VectorIndex

pytestmark = pytest.mark.integration  # skipped if no Postgres (uses session fixture)


async def test_upsert_then_search_returns_hit(vector_index: VectorIndex) -> None:
    embedder = MockEmbedder()
    shop_id = uuid4()
    pid = uuid4()
    [vec] = await embedder.embed(["red running shoe"])
    await vector_index.upsert(
        shop_id=shop_id,
        product_id=pid,
        vector=vec,
        payload={"name": "Red Shoe", "stock_status": "instock"},
    )
    [query_vec] = await embedder.embed(["red running shoe"])
    hits = await vector_index.search(shop_id=shop_id, vector=query_vec, top_k=5)
    assert len(hits) == 1
    assert hits[0].product_id == pid


async def test_search_isolates_by_shop(vector_index: VectorIndex) -> None:
    embedder = MockEmbedder()
    shop_a = uuid4()
    shop_b = uuid4()
    pid_a = uuid4()
    [vec] = await embedder.embed(["shoe"])
    await vector_index.upsert(
        shop_id=shop_a,
        product_id=pid_a,
        vector=vec,
        payload={"name": "A's shoe", "stock_status": "instock"},
    )
    [q] = await embedder.embed(["shoe"])
    hits_b = await vector_index.search(shop_id=shop_b, vector=q, top_k=5)
    assert hits_b == []


async def test_search_filters_out_of_stock(vector_index: VectorIndex) -> None:
    embedder = MockEmbedder()
    shop = uuid4()
    instock = uuid4()
    oos = uuid4()
    [v_in] = await embedder.embed(["running shoe instock"])
    [v_oos] = await embedder.embed(["running shoe outofstock"])
    await vector_index.upsert(
        shop_id=shop, product_id=instock, vector=v_in,
        payload={"name": "in", "stock_status": "instock"},
    )
    await vector_index.upsert(
        shop_id=shop, product_id=oos, vector=v_oos,
        payload={"name": "out", "stock_status": "outofstock"},
    )
    [q] = await embedder.embed(["running shoe"])
    hits = await vector_index.search(shop_id=shop, vector=q, top_k=5, in_stock_only=True)
    assert all(h.product_id == instock for h in hits)


async def test_delete_removes_from_search(vector_index: VectorIndex) -> None:
    embedder = MockEmbedder()
    shop = uuid4()
    pid = uuid4()
    [v] = await embedder.embed(["thing"])
    await vector_index.upsert(
        shop_id=shop, product_id=pid, vector=v,
        payload={"name": "x", "stock_status": "instock"},
    )
    await vector_index.delete(shop_id=shop, product_id=pid)
    [q] = await embedder.embed(["thing"])
    hits = await vector_index.search(shop_id=shop, vector=q, top_k=5)
    assert hits == []
