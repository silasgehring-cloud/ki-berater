from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.billing.service import is_within_quota
from backend.db.tenant_query import tenant_select
from backend.embeddings.embedder import Embedder
from backend.llm.cost_tracker import record_usage
from backend.llm.router import Router
from backend.llm.types import ChatMessage, CompletionResult
from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.models.product import Product
from backend.models.shop import Shop
from backend.prompts.system_prompt import build_system_prompt, wrap_user_query
from backend.schemas.conversation import ConversationCreate
from backend.vectordb.qdrant_client import VectorIndex

logger = structlog.get_logger("backend.conversation")

_TOP_K_PRODUCTS = 5


class QuotaExceededError(Exception):
    """Plan's monthly conversation limit reached. Endpoints map this to 402."""


def _to_chat_history(
    persisted: list[Message], wrap_last_user: bool = True
) -> list[ChatMessage]:
    out: list[ChatMessage] = []
    last_user_idx = max(
        (i for i, m in enumerate(persisted) if m.role == "user"), default=-1
    )
    for i, m in enumerate(persisted):
        role: Literal["user", "assistant"] = "user" if m.role == "user" else "assistant"
        content = m.content
        if wrap_last_user and i == last_user_idx and role == "user":
            content = wrap_user_query(content)
        out.append(ChatMessage(role=role, content=content))
    return out


def _format_product_context(products: list[Product]) -> str:
    if not products:
        return ""
    lines: list[str] = []
    for p in products:
        price = f"{p.price:.2f} {p.currency}" if p.price is not None else "Preis auf Anfrage"
        cats = ", ".join(p.categories) if p.categories else ""
        snippet = p.description[:200] + ("…" if len(p.description) > 200 else "")
        url = p.url or ""
        lines.append(
            f"- ID={p.id} | {p.name} ({price})\n"
            f"  Kategorien: {cats}\n"
            f"  Beschreibung: {snippet}\n"
            f"  URL: {url}"
        )
    return "\n".join(lines)


async def _retrieve_relevant_products(
    db: AsyncSession,
    *,
    shop: Shop,
    last_user_msg: str,
    embedder: Embedder | None,
    vector_index: VectorIndex | None,
) -> list[Product]:
    """Vector-search top-K, then re-fetch from Postgres to filter deleted/oos."""
    if embedder is None or vector_index is None or not last_user_msg.strip():
        return []
    vectors = await embedder.embed([last_user_msg])
    if not vectors:
        return []
    hits = await vector_index.search(
        shop_id=shop.id, vector=vectors[0], top_k=_TOP_K_PRODUCTS
    )
    if not hits:
        return []
    ids = [h.product_id for h in hits]
    stmt = (
        tenant_select(Product, shop_id=shop.id)
        .where(Product.id.in_(ids))
        .where(Product.deleted.is_(False))
    )
    rows = list((await db.execute(stmt)).scalars().all())
    # Preserve Qdrant ranking order.
    by_id = {r.id: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]


async def _generate_reply(
    db: AsyncSession,
    *,
    shop: Shop,
    conversation: Conversation,
    history_orm: list[Message],
    router: Router,
    embedder: Embedder | None,
    vector_index: VectorIndex | None,
) -> tuple[Message, list[Product]]:
    last_user = next((m for m in reversed(history_orm) if m.role == "user"), None)
    last_user_text = last_user.content if last_user else ""

    relevant = await _retrieve_relevant_products(
        db,
        shop=shop,
        last_user_msg=last_user_text,
        embedder=embedder,
        vector_index=vector_index,
    )
    system = build_system_prompt(shop, product_context=_format_product_context(relevant))
    chat_history = _to_chat_history(history_orm)
    result = await router.complete(system=system, history=chat_history)

    assistant = Message(
        shop_id=shop.id,
        conversation_id=conversation.id,
        role="assistant",
        content=result.text,
        products_referenced=[p.id for p in relevant] or None,
    )
    db.add(assistant)
    await record_usage(
        db, shop_id=shop.id, conversation_id=conversation.id, result=result
    )
    return assistant, relevant


async def create_conversation(
    db: AsyncSession,
    shop: Shop,
    payload: ConversationCreate,
    router: Router,
    embedder: Embedder | None = None,
    vector_index: VectorIndex | None = None,
) -> tuple[Conversation, Message, Message]:
    if not await is_within_quota(db, shop):
        raise QuotaExceededError(f"plan {shop.plan!r} monthly limit reached")
    convo = Conversation(shop_id=shop.id, visitor_id=payload.visitor_id)
    db.add(convo)
    await db.flush()

    user_msg = Message(
        shop_id=shop.id,
        conversation_id=convo.id,
        role="user",
        content=payload.initial_message,
    )
    db.add(user_msg)
    await db.flush()

    assistant, _products = await _generate_reply(
        db,
        shop=shop,
        conversation=convo,
        history_orm=[user_msg],
        router=router,
        embedder=embedder,
        vector_index=vector_index,
    )
    await db.commit()
    await db.refresh(convo)
    await db.refresh(user_msg)
    await db.refresh(assistant)
    return convo, user_msg, assistant


async def append_message(
    db: AsyncSession,
    shop: Shop,
    conversation_id: UUID,
    user_content: str,
    router: Router,
    embedder: Embedder | None = None,
    vector_index: VectorIndex | None = None,
) -> tuple[Message, Message] | None:
    convo_stmt = tenant_select(Conversation, shop_id=shop.id).where(
        Conversation.id == conversation_id
    )
    convo = (await db.execute(convo_stmt)).scalar_one_or_none()
    if convo is None:
        return None

    user_msg = Message(
        shop_id=shop.id,
        conversation_id=convo.id,
        role="user",
        content=user_content,
    )
    db.add(user_msg)
    await db.flush()

    history_stmt = (
        tenant_select(Message, shop_id=shop.id)
        .where(Message.conversation_id == convo.id)
        .order_by(Message.created_at)
    )
    history = list((await db.execute(history_stmt)).scalars().all())

    assistant, _products = await _generate_reply(
        db,
        shop=shop,
        conversation=convo,
        history_orm=history,
        router=router,
        embedder=embedder,
        vector_index=vector_index,
    )
    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant)
    return user_msg, assistant


async def get_conversation(
    db: AsyncSession, shop_id: UUID, conversation_id: UUID
) -> Conversation | None:
    stmt = tenant_select(Conversation, shop_id=shop_id).where(
        Conversation.id == conversation_id
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_messages(
    db: AsyncSession, shop_id: UUID, conversation_id: UUID
) -> list[Message]:
    stmt = (
        tenant_select(Message, shop_id=shop_id)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list((await db.execute(stmt)).scalars().all())


@dataclass
class StreamEvent:
    """Single SSE-bound event emitted by the streaming services."""

    type: Literal["start", "chunk", "end", "error"]
    data: dict[str, object]


async def _stream_reply(
    db: AsyncSession,
    *,
    shop: Shop,
    conversation: Conversation,
    user_msg: Message,
    history_orm: list[Message],
    router: Router,
    embedder: Embedder | None,
    vector_index: VectorIndex | None,
) -> AsyncIterator[StreamEvent]:
    last_user = next((m for m in reversed(history_orm) if m.role == "user"), None)
    last_user_text = last_user.content if last_user else ""
    relevant = await _retrieve_relevant_products(
        db,
        shop=shop,
        last_user_msg=last_user_text,
        embedder=embedder,
        vector_index=vector_index,
    )
    system = build_system_prompt(shop, product_context=_format_product_context(relevant))
    chat_history = _to_chat_history(history_orm)
    assistant_id = uuid4()
    product_ids = [p.id for p in relevant]

    yield StreamEvent(
        "start",
        {
            "conversation_id": str(conversation.id),
            "user_message_id": str(user_msg.id),
            "assistant_message_id": str(assistant_id),
            "products": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "price": str(p.price) if p.price is not None else None,
                    "currency": p.currency,
                    "url": p.url,
                    "image_url": p.image_url,
                }
                for p in relevant
            ],
        },
    )

    full_text_parts: list[str] = []
    final: CompletionResult | None = None
    try:
        async for chunk in router.stream(system=system, history=chat_history):
            if chunk.delta:
                full_text_parts.append(chunk.delta)
                yield StreamEvent("chunk", {"delta": chunk.delta})
            if chunk.final is not None:
                final = chunk.final
    except Exception as exc:
        yield StreamEvent("error", {"detail": str(exc)})
        return

    full_text = "".join(full_text_parts)
    assistant = Message(
        id=assistant_id,
        shop_id=shop.id,
        conversation_id=conversation.id,
        role="assistant",
        content=full_text,
        products_referenced=product_ids or None,
    )
    db.add(assistant)
    if final is not None:
        await record_usage(
            db, shop_id=shop.id, conversation_id=conversation.id, result=final
        )
    await db.commit()

    yield StreamEvent(
        "end",
        {
            "model": final.model_id if final else "",
            "input_tokens": final.input_tokens if final else 0,
            "output_tokens": final.output_tokens if final else 0,
            "cached_tokens": final.cached_tokens if final else 0,
            "latency_ms": final.latency_ms if final else 0,
        },
    )


async def stream_create_conversation(
    db: AsyncSession,
    shop: Shop,
    payload: ConversationCreate,
    router: Router,
    embedder: Embedder | None = None,
    vector_index: VectorIndex | None = None,
) -> AsyncIterator[StreamEvent]:
    if not await is_within_quota(db, shop):
        yield StreamEvent("error", {
            "detail": f"plan {shop.plan!r} monthly limit reached",
            "code": "quota_exceeded",
        })
        return
    convo = Conversation(shop_id=shop.id, visitor_id=payload.visitor_id)
    db.add(convo)
    await db.flush()
    user_msg = Message(
        shop_id=shop.id,
        conversation_id=convo.id,
        role="user",
        content=payload.initial_message,
    )
    db.add(user_msg)
    await db.flush()

    async for ev in _stream_reply(
        db,
        shop=shop,
        conversation=convo,
        user_msg=user_msg,
        history_orm=[user_msg],
        router=router,
        embedder=embedder,
        vector_index=vector_index,
    ):
        yield ev


async def stream_append_message(
    db: AsyncSession,
    shop: Shop,
    conversation_id: UUID,
    user_content: str,
    router: Router,
    embedder: Embedder | None = None,
    vector_index: VectorIndex | None = None,
) -> AsyncIterator[StreamEvent]:
    convo_stmt = tenant_select(Conversation, shop_id=shop.id).where(
        Conversation.id == conversation_id
    )
    convo = (await db.execute(convo_stmt)).scalar_one_or_none()
    if convo is None:
        yield StreamEvent("error", {"detail": "conversation not found"})
        return

    user_msg = Message(
        shop_id=shop.id,
        conversation_id=convo.id,
        role="user",
        content=user_content,
    )
    db.add(user_msg)
    await db.flush()

    history_stmt = (
        tenant_select(Message, shop_id=shop.id)
        .where(Message.conversation_id == convo.id)
        .order_by(Message.created_at)
    )
    history = list((await db.execute(history_stmt)).scalars().all())

    async for ev in _stream_reply(
        db,
        shop=shop,
        conversation=convo,
        user_msg=user_msg,
        history_orm=history,
        router=router,
        embedder=embedder,
        vector_index=vector_index,
    ):
        yield ev


__all__ = [
    "StreamEvent",
    "append_message",
    "create_conversation",
    "get_conversation",
    "list_messages",
    "stream_append_message",
    "stream_create_conversation",
]
