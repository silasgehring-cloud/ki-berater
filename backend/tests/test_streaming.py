"""SSE streaming tests."""
from __future__ import annotations

import json
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.llm.providers.mock import MockProvider
from backend.llm.router import AllProvidersFailedError, Router
from backend.llm.types import ChatMessage
from backend.models.llm_usage import LLMUsage
from backend.models.message import Message
from backend.tests.conftest import TEST_ADMIN_KEY

pytestmark = pytest.mark.integration


def _msg(role: str, content: str) -> ChatMessage:
    return ChatMessage(role=role, content=content)  # type: ignore[arg-type]


# ---- Provider-level streaming ----


async def test_mock_provider_emits_chunks_then_final() -> None:
    p = MockProvider(response="Hallo Welt", stream_chunk_size=3)
    chunks = []
    async for c in p.stream("sys", [_msg("user", "hi")]):
        chunks.append(c)
    deltas = [c.delta for c in chunks if c.delta]
    finals = [c.final for c in chunks if c.final is not None]
    assert "".join(deltas) == "Hallo Welt"
    assert len(finals) == 1
    assert finals[0].text == "Hallo Welt"
    assert finals[0].output_tokens > 0


# ---- Router-level streaming ----


async def test_router_stream_uses_first_provider() -> None:
    primary = MockProvider(response="primary stream")
    fallback = MockProvider(response="fallback stream")
    router = Router(
        providers={"a": primary, "b": fallback},
        chains={"standard": ["a", "b"], "complex": ["a", "b"]},
    )
    deltas = []
    async for c in router.stream("sys", [_msg("user", "hi")]):
        if c.delta:
            deltas.append(c.delta)
    assert "".join(deltas) == "primary stream"
    assert len(primary.stream_calls) == 1
    assert len(fallback.stream_calls) == 0


async def test_router_stream_falls_back_before_first_chunk() -> None:
    failing = MockProvider(raise_error=True)
    fallback = MockProvider(response="recovered")
    router = Router(
        providers={"a": failing, "b": fallback},
        chains={"standard": ["a", "b"], "complex": ["a", "b"]},
    )
    deltas = []
    async for c in router.stream("sys", [_msg("user", "hi")]):
        if c.delta:
            deltas.append(c.delta)
    assert "".join(deltas) == "recovered"


async def test_router_stream_raises_when_all_fail() -> None:
    a = MockProvider(raise_error=True)
    b = MockProvider(raise_error=True)
    router = Router(
        providers={"a": a, "b": b},
        chains={"standard": ["a", "b"], "complex": ["a", "b"]},
    )
    with pytest.raises(AllProvidersFailedError):
        async for _ in router.stream("sys", [_msg("user", "hi")]):
            pass


# ---- HTTP integration ----


async def _new_shop(client: AsyncClient, domain: str) -> dict[str, Any]:
    resp = await client.post(
        "/v1/shops",
        json={"domain": domain},
        headers={"X-Admin-Key": TEST_ADMIN_KEY},
    )
    assert resp.status_code == 201, resp.text
    body: dict[str, Any] = resp.json()
    return body


def _parse_sse(payload: str) -> list[dict[str, Any]]:
    """Parse `event: NAME\\ndata: JSON\\n\\n` blocks into dicts."""
    out: list[dict[str, Any]] = []
    for block in payload.split("\n\n"):
        if not block.strip():
            continue
        ev_type = ""
        data_str = ""
        for line in block.splitlines():
            if line.startswith("event:"):
                ev_type = line[6:].strip()
            elif line.startswith("data:"):
                data_str = line[5:].strip()
        if ev_type and data_str:
            out.append({"type": ev_type, "data": json.loads(data_str)})
    return out


async def test_stream_create_conversation_emits_start_chunks_end(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "stream-1.example.com")
    resp = await integration_client.post(
        "/v1/conversations/stream",
        json={"initial_message": "Hallo"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    types = [e["type"] for e in events]
    assert types[0] == "start"
    assert "chunk" in types
    assert types[-1] == "end"

    full_text = "".join(
        e["data"]["delta"] for e in events if e["type"] == "chunk"
    )
    assert len(full_text) > 0


async def test_stream_persists_assistant_message_and_usage(
    integration_client: AsyncClient,
    db: AsyncSession,
) -> None:
    shop = await _new_shop(integration_client, "stream-persist.example.com")
    resp = await integration_client.post(
        "/v1/conversations/stream",
        json={"initial_message": "Hallo Streaming-Welt"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert resp.status_code == 200

    msgs = list((await db.execute(select(Message).order_by(Message.created_at))).scalars().all())
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[1].content  # assistant content was persisted

    usage = list((await db.execute(select(LLMUsage))).scalars().all())
    assert len(usage) == 1
    assert usage[0].model == "mock-1"


async def test_stream_append_to_unknown_conversation_emits_error_event(
    integration_client: AsyncClient,
) -> None:
    shop = await _new_shop(integration_client, "stream-err.example.com")
    resp = await integration_client.post(
        "/v1/conversations/00000000-0000-0000-0000-000000000000/messages/stream",
        json={"content": "noop"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    # The streaming endpoint always returns 200 — errors are events in the stream.
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    assert any(e["type"] == "error" for e in events)


async def test_stream_followup_uses_history(integration_client: AsyncClient) -> None:
    shop = await _new_shop(integration_client, "stream-follow.example.com")
    create = await integration_client.post(
        "/v1/conversations/stream",
        json={"initial_message": "Erste Nachricht"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    start_event = _parse_sse(create.text)[0]
    convo_id = start_event["data"]["conversation_id"]

    follow = await integration_client.post(
        f"/v1/conversations/{convo_id}/messages/stream",
        json={"content": "Folge"},
        headers={"X-Api-Key": shop["api_key"]},
    )
    assert follow.status_code == 200
    events = _parse_sse(follow.text)
    assert events[0]["type"] == "start"
    assert events[-1]["type"] == "end"
