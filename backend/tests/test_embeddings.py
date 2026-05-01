"""Mock embedder properties + dimensionality."""
from backend.embeddings.embedder import EMBEDDING_DIM, MockEmbedder


async def test_mock_embed_returns_correct_dim() -> None:
    e = MockEmbedder()
    [vec] = await e.embed(["hello"])
    assert len(vec) == EMBEDDING_DIM
    assert all(-1.0 <= x <= 1.0 for x in vec)


async def test_mock_embed_is_deterministic() -> None:
    e = MockEmbedder()
    [v1] = await e.embed(["same text"])
    [v2] = await e.embed(["same text"])
    assert v1 == v2


async def test_mock_embed_different_texts_yield_different_vectors() -> None:
    e = MockEmbedder()
    [v_a] = await e.embed(["red shoes"])
    [v_b] = await e.embed(["blue jacket"])
    assert v_a != v_b


async def test_mock_embed_handles_empty_input() -> None:
    e = MockEmbedder()
    out = await e.embed([])
    assert out == []
