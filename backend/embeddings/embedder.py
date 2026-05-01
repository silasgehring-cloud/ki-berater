"""Text embedder via Gemini text-embedding-004 (768-dim, cosine distance).

The embedder is the only sanctioned way to produce vectors. Tests use
`MockEmbedder` which is deterministic and offline.
"""
from __future__ import annotations

import hashlib
from typing import Protocol

from google import genai
from google.genai import types as genai_types

EMBEDDING_DIM = 768
EMBEDDING_MODEL = "text-embedding-004"


class Embedder(Protocol):
    dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class GeminiEmbedder:
    name = "gemini"
    dim = EMBEDDING_DIM
    model_id = EMBEDDING_MODEL

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not configured")
        self._client = genai.Client(api_key=api_key)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = await self._client.aio.models.embed_content(
            model=self.model_id,
            contents=texts,
            config=genai_types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=EMBEDDING_DIM,
            ),
        )
        return [list(e.values or []) for e in (resp.embeddings or [])]


class MockEmbedder:
    """Deterministic embedder for tests. Hashes text → fixed-size float vector."""

    name = "mock"
    dim = EMBEDDING_DIM

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        # SHA-512 = 512 bits = 64 bytes; we tile to fill 768 floats in [-1, 1].
        digest = hashlib.sha512(text.encode("utf-8")).digest()
        out: list[float] = []
        i = 0
        while len(out) < EMBEDDING_DIM:
            byte = digest[i % len(digest)]
            out.append((byte / 127.5) - 1.0)
            i += 1
        return out
