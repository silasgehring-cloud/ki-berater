"""FastAPI dependencies: auth + DB session + LLM router + embedder + vector index."""
import hmac
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import settings
from backend.db.session import get_session, get_sessionmaker
from backend.embeddings.embedder import Embedder, GeminiEmbedder, MockEmbedder
from backend.llm.bootstrap import build_default_router
from backend.llm.router import Router
from backend.models.shop import Shop
from backend.services.shop_service import find_shop_by_api_key
from backend.vectordb.qdrant_client import VectorIndex

_router_singleton: Router | None = None
_embedder_singleton: Embedder | None = None
_vector_singleton: VectorIndex | None = None


def get_router() -> Router:
    global _router_singleton
    if _router_singleton is None:
        _router_singleton = build_default_router()
    return _router_singleton


def get_embedder() -> Embedder:
    """Real Gemini embedder if GOOGLE_API_KEY is set, else MockEmbedder.

    Tests override this dependency directly via app.dependency_overrides.
    """
    global _embedder_singleton
    if _embedder_singleton is None:
        if settings.google_api_key:
            _embedder_singleton = GeminiEmbedder(api_key=settings.google_api_key)
        else:
            _embedder_singleton = MockEmbedder()
    return _embedder_singleton


def get_vector_index() -> VectorIndex:
    global _vector_singleton
    if _vector_singleton is None:
        _vector_singleton = VectorIndex.from_url(settings.qdrant_mode)
    return _vector_singleton


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return get_sessionmaker()


LlmRouter = Annotated[Router, Depends(get_router)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
VectorIndexDep = Annotated[VectorIndex, Depends(get_vector_index)]
SessionFactoryDep = Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)]


async def db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


DbSession = Annotated[AsyncSession, Depends(db_session)]


async def get_current_shop(
    db: DbSession,
    x_api_key: Annotated[str | None, Header(alias="X-Api-Key")] = None,
) -> Shop:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing X-Api-Key header",
        )
    shop = await find_shop_by_api_key(db, x_api_key)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid API key",
        )
    return shop


CurrentShop = Annotated[Shop, Depends(get_current_shop)]


async def require_admin(
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
) -> None:
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="admin endpoint disabled (ADMIN_API_KEY not configured)",
        )
    # Constant-time compare prevents timing-based admin-key enumeration.
    provided = (x_admin_key or "").encode("utf-8")
    expected = settings.admin_api_key.encode("utf-8")
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin key",
        )
