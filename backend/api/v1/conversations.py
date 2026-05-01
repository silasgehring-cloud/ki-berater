import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.api.deps import (
    CurrentShop,
    DbSession,
    EmbedderDep,
    LlmRouter,
    VectorIndexDep,
)
from backend.schemas.analytics import ClickEvent, ClickRead, ConversionEvent
from backend.schemas.conversation import (
    ConversationCreate,
    ConversationCreated,
    ConversationRead,
)
from backend.schemas.message import MessageCreate, MessageExchange, MessageRead
from backend.services.analytics_service import record_click, record_conversion
from backend.services.conversation_service import (
    QuotaExceededError,
    StreamEvent,
    append_message,
    create_conversation,
    get_conversation,
    stream_append_message,
    stream_create_conversation,
)

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


@router.post(
    "",
    response_model=ConversationCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation_endpoint(
    payload: ConversationCreate,
    db: DbSession,
    shop: CurrentShop,
    llm: LlmRouter,
    embedder: EmbedderDep,
    vector_index: VectorIndexDep,
) -> ConversationCreated:
    try:
        convo, user_msg, assistant_msg = await create_conversation(
            db, shop, payload, llm,
            embedder=embedder, vector_index=vector_index,
        )
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "quota_exceeded", "message": str(exc)},
        ) from exc
    return ConversationCreated(
        conversation=ConversationRead.model_validate(convo),
        user_message=MessageRead.model_validate(user_msg),
        assistant_message=MessageRead.model_validate(assistant_msg),
    )


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation_endpoint(
    conversation_id: UUID,
    db: DbSession,
    shop: CurrentShop,
) -> ConversationRead:
    convo = await get_conversation(db, shop.id, conversation_id)
    if convo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return ConversationRead.model_validate(convo)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageExchange,
    status_code=status.HTTP_201_CREATED,
)
async def append_message_endpoint(
    conversation_id: UUID,
    payload: MessageCreate,
    db: DbSession,
    shop: CurrentShop,
    llm: LlmRouter,
    embedder: EmbedderDep,
    vector_index: VectorIndexDep,
) -> MessageExchange:
    result = await append_message(
        db, shop, conversation_id, payload.content, llm,
        embedder=embedder, vector_index=vector_index,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    user_msg, assistant_msg = result
    return MessageExchange(
        user_message=MessageRead.model_validate(user_msg),
        assistant_message=MessageRead.model_validate(assistant_msg),
    )


def _format_sse(ev: StreamEvent) -> bytes:
    return f"event: {ev.type}\ndata: {json.dumps(ev.data, separators=(',', ':'))}\n\n".encode()


async def _to_sse_bytes(events: AsyncIterator[StreamEvent]) -> AsyncIterator[bytes]:
    async for ev in events:
        yield _format_sse(ev)


_SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


@router.post("/stream", status_code=status.HTTP_200_OK)
async def stream_create_conversation_endpoint(
    payload: ConversationCreate,
    db: DbSession,
    shop: CurrentShop,
    llm: LlmRouter,
    embedder: EmbedderDep,
    vector_index: VectorIndexDep,
) -> StreamingResponse:
    events = stream_create_conversation(
        db, shop, payload, llm, embedder=embedder, vector_index=vector_index
    )
    return StreamingResponse(
        _to_sse_bytes(events),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post(
    "/{conversation_id}/clicks",
    response_model=ClickRead,
    status_code=status.HTTP_201_CREATED,
)
async def record_click_endpoint(
    conversation_id: UUID,
    payload: ClickEvent,
    db: DbSession,
    shop: CurrentShop,
) -> ClickRead:
    click = await record_click(
        db,
        shop=shop,
        conversation_id=conversation_id,
        product_id=payload.product_id,
        message_id=payload.message_id,
    )
    if click is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return ClickRead.model_validate(click)


@router.post("/{conversation_id}/conversion", response_model=ConversationRead)
async def mark_conversation_converted(
    conversation_id: UUID,
    payload: ConversionEvent,
    db: DbSession,
    shop: CurrentShop,
) -> ConversationRead:
    convo, result = await record_conversion(db, shop, conversation_id, payload)
    if convo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    _ = result  # idempotency-status reserved for future logging/metrics
    return ConversationRead.model_validate(convo)


@router.post("/{conversation_id}/messages/stream", status_code=status.HTTP_200_OK)
async def stream_append_message_endpoint(
    conversation_id: UUID,
    payload: MessageCreate,
    db: DbSession,
    shop: CurrentShop,
    llm: LlmRouter,
    embedder: EmbedderDep,
    vector_index: VectorIndexDep,
) -> StreamingResponse:
    events = stream_append_message(
        db, shop, conversation_id, payload.content, llm,
        embedder=embedder, vector_index=vector_index,
    )
    return StreamingResponse(
        _to_sse_bytes(events),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
