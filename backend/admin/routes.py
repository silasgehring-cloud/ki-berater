"""Admin UI routes.

All under /admin/. Login via cookie (token == ADMIN_API_KEY), validated
against settings on every request. Templates server-rendered with Jinja2,
HTMX takes over the few interactive bits (shop create form).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.admin import auth as admin_auth
from backend.admin.queries import (
    fetch_conversation_with_messages,
    fetch_conversations,
    fetch_global_overview,
    fetch_recent_conversations,
    fetch_shop,
    fetch_shop_rows,
)
from backend.api.deps import DbSession
from backend.core.config import settings
from backend.models.conversation import Conversation
from backend.models.product import Product
from backend.models.shop import Shop
from backend.schemas.shop import ShopCreate
from backend.services.shop_service import create_shop
from backend.vectordb.qdrant_client import VectorIndex

_HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(_HERE / "templates"))

router = APIRouter(prefix="/admin", tags=["admin-ui"], include_in_schema=False)


def _ctx(**extra: object) -> dict[str, object]:
    """Default template context shared across pages."""
    return {
        "api_version": settings.api_version,
        **extra,
    }


def _render(
    request: Request,
    name: str,
    extra: dict[str, object] | None = None,
    *,
    status_code: int = 200,
) -> Response:
    """Wraps Jinja2Templates.TemplateResponse with the new (request, name, ctx) signature."""
    ctx = _ctx(**(extra or {}))
    return templates.TemplateResponse(
        request, name, ctx, status_code=status_code
    )


# ----------------------------------------------------------------------
# Auth pages
# ----------------------------------------------------------------------


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request, next: str = "/admin/", error: str | None = None
) -> Response:
    return _render(
        request,
        "login.html",
        {"next": next, "error": error, "admin_key_set": bool(settings.admin_api_key)},
    )


@router.post("/login")
async def login_submit(
    request: Request,
    token: Annotated[str, Form()],
    next: Annotated[str, Form()] = "/admin/",
) -> Response:
    if not admin_auth.is_authenticated(token):
        return _render(
            request,
            "login.html",
            {
                "next": next,
                "error": "Falscher Token.",
                "admin_key_set": bool(settings.admin_api_key),
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Only redirect to same-origin paths to prevent open-redirect.
    redirect_to = next if next.startswith("/admin") else "/admin/"
    response = RedirectResponse(url=redirect_to, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        admin_auth.COOKIE_NAME,
        token,
        max_age=60 * 60 * 24 * 14,  # 14 days
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/admin",
    )
    return response


@router.post("/logout")
async def logout() -> Response:
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(admin_auth.COOKIE_NAME, path="/admin")
    return response


# ----------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(admin_auth.require_admin_session)])
async def dashboard(request: Request, db: DbSession) -> Response:
    overview = await fetch_global_overview(db)
    conversations = await fetch_conversations(db, limit=20)
    return _render(
        request,
        "dashboard.html",
        {"active": "dashboard", "overview": overview, "conversations": conversations},
    )


# ----------------------------------------------------------------------
# Shops
# ----------------------------------------------------------------------


@router.get(
    "/shops",
    response_class=HTMLResponse,
    dependencies=[Depends(admin_auth.require_admin_session)],
)
async def shops_list(request: Request, db: DbSession) -> Response:
    rows = await fetch_shop_rows(db)
    return _render(request, "shops.html", {"active": "shops", "rows": rows})


@router.post(
    "/shops",
    response_class=HTMLResponse,
    dependencies=[Depends(admin_auth.require_admin_session)],
)
async def shops_create(
    request: Request,
    db: DbSession,
    domain: Annotated[str, Form()],
    plan: Annotated[str, Form()] = "starter",
) -> Response:
    """HTMX endpoint — returns the create-result fragment."""
    domain = domain.strip().lower()
    try:
        payload = ShopCreate(domain=domain, plan=plan)
    except Exception as e:  # pydantic ValidationError
        return _render(
            request,
            "_shop_create_result.html",
            {"error": f"Ungültige Eingabe: {e}"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        shop, plain_key, webhook_secret = await create_shop(db, payload)
    except IntegrityError:
        await db.rollback()
        return _render(
            request,
            "_shop_create_result.html",
            {"error": f"Domain '{domain}' existiert bereits."},
            status_code=status.HTTP_409_CONFLICT,
        )

    return _render(
        request,
        "_shop_create_result.html",
        {"shop_id": shop.id, "api_key": plain_key, "webhook_secret": webhook_secret},
    )


@router.get(
    "/shops/{shop_id}",
    response_class=HTMLResponse,
    dependencies=[Depends(admin_auth.require_admin_session)],
)
async def shop_detail(request: Request, db: DbSession, shop_id: UUID) -> Response:
    shop = await fetch_shop(db, shop_id)
    if shop is None:
        raise HTTPException(status_code=404, detail="shop not found")

    end = datetime.now(UTC)
    start = end - timedelta(days=30)

    convo_total = (
        await db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(
                Conversation.shop_id == shop.id,
                Conversation.started_at >= start,
                Conversation.started_at < end,
            )
        )
    ) or 0
    converted = (
        await db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(
                Conversation.shop_id == shop.id,
                Conversation.started_at >= start,
                Conversation.started_at < end,
                Conversation.converted.is_(True),
            )
        )
    ) or 0
    revenue = (
        await db.scalar(
            select(func.coalesce(func.sum(Conversation.order_total_eur), 0))
            .where(
                Conversation.shop_id == shop.id,
                Conversation.started_at >= start,
                Conversation.started_at < end,
                Conversation.converted.is_(True),
            )
        )
    ) or Decimal("0")
    products = (
        await db.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.shop_id == shop.id)
        )
    ) or 0

    rate = round((converted / convo_total) * 100, 2) if convo_total else 0.0
    stats = {
        "conversations_30d": int(convo_total),
        "converted_30d": int(converted),
        "conversion_rate_30d": rate,
        "revenue_30d_eur": Decimal(str(revenue)),
        "product_count": int(products),
    }

    conversations = await fetch_recent_conversations(db, shop.id, limit=10)

    return _render(
        request,
        "shop_detail.html",
        {"active": "shops", "shop": shop, "stats": stats, "conversations": conversations},
    )


# ----------------------------------------------------------------------
# Conversations
# ----------------------------------------------------------------------


@router.get(
    "/conversations",
    response_class=HTMLResponse,
    dependencies=[Depends(admin_auth.require_admin_session)],
)
async def conversations_list(
    request: Request,
    db: DbSession,
    shop_id: str | None = None,
    converted: str | None = None,
) -> Response:
    shop_uuid: UUID | None = None
    if shop_id:
        try:
            shop_uuid = UUID(shop_id)
        except ValueError:
            shop_uuid = None

    converted_filter: bool | None = None
    if converted == "1":
        converted_filter = True
    elif converted == "0":
        converted_filter = False

    rows = await fetch_conversations(
        db, shop_id=shop_uuid, converted=converted_filter, limit=200
    )
    shops = (await db.execute(select(Shop).order_by(Shop.domain))).scalars().all()

    return _render(
        request,
        "conversations.html",
        {
            "active": "conversations",
            "rows": rows,
            "shops": shops,
            "str_filters": {"shop_id": shop_id or "", "converted": converted or ""},
        },
    )


@router.get(
    "/conversations/{conversation_id}",
    response_class=HTMLResponse,
    dependencies=[Depends(admin_auth.require_admin_session)],
)
async def conversation_detail(
    request: Request, db: DbSession, conversation_id: UUID
) -> Response:
    found = await fetch_conversation_with_messages(db, conversation_id)
    if found is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    convo, shop, messages = found
    return _render(
        request,
        "conversation_detail.html",
        {"active": "conversations", "convo": convo, "shop": shop, "messages": messages},
    )


# ----------------------------------------------------------------------
# Health / system
# ----------------------------------------------------------------------


@router.get(
    "/health",
    response_class=HTMLResponse,
    dependencies=[Depends(admin_auth.require_admin_session)],
)
async def health_page(request: Request, db: DbSession) -> Response:
    checks: list[dict[str, str]] = []

    # Postgres
    try:
        await db.execute(select(1))
        checks.append({"name": "PostgreSQL", "status": "ok", "detail": "SELECT 1 ok", "label": ""})
    except Exception as e:  # noqa: BLE001
        checks.append({"name": "PostgreSQL", "status": "err", "detail": str(e)[:120], "label": "fehler"})

    # Qdrant — try a simple call on the singleton vector index
    from backend.api.deps import get_vector_index

    try:
        idx: VectorIndex = get_vector_index()
        await idx.ensure_collection()
        mode = settings.qdrant_mode or ":memory:"
        checks.append({"name": "Qdrant (Vektor-DB)", "status": "ok", "detail": mode, "label": ""})
    except Exception as e:  # noqa: BLE001
        checks.append({"name": "Qdrant (Vektor-DB)", "status": "err", "detail": str(e)[:120], "label": "fehler"})

    # Redis (best effort — only if URL points somewhere reachable)
    if settings.redis_url and not settings.redis_url.startswith("redis://localhost"):
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url, socket_timeout=2)
            try:
                pong = await r.ping()
                checks.append({"name": "Redis", "status": "ok" if pong else "warn", "detail": settings.redis_url, "label": "kein PONG"})
            finally:
                await r.aclose()
        except Exception as e:  # noqa: BLE001
            checks.append({"name": "Redis", "status": "warn", "detail": str(e)[:120], "label": "nicht erreichbar"})
    else:
        checks.append({"name": "Redis", "status": "warn", "detail": settings.redis_url or "(leer)", "label": "lokal/aus"})

    api_keys = [
        {"name": "ANTHROPIC_API_KEY", "set": bool(settings.anthropic_api_key), "note": "Claude-LLM"},
        {"name": "GOOGLE_API_KEY", "set": bool(settings.google_api_key), "note": "Gemini + Embeddings"},
        {"name": "OPENAI_API_KEY", "set": bool(settings.openai_api_key), "note": "Fallback-LLM"},
        {"name": "ADMIN_API_KEY", "set": bool(settings.admin_api_key), "note": "dieses Admin-UI"},
    ]

    return _render(
        request,
        "health.html",
        {
            "active": "health",
            "environment": settings.environment,
            "retention_days": settings.retention_days,
            "retention_loop_enabled": settings.retention_loop_enabled,
            "checks": checks,
            "api_keys": api_keys,
            "sentry_dsn_set": bool(settings.sentry_dsn),
            "stripe_set": bool(settings.stripe_api_key),
            "rate_limit_storage": settings.rate_limit_storage_uri or "in-memory",
            "rate_limit_default": settings.rate_limit_default,
        },
    )
