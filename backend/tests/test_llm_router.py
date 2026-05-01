"""Router heuristic + fallback chain. Pure unit tests, no DB."""
import pytest

from backend.llm.providers.mock import MockProvider
from backend.llm.router import (
    AllProvidersFailedError,
    Router,
    classify_complexity,
)
from backend.llm.types import ChatMessage


def _msg(role: str, content: str) -> ChatMessage:
    return ChatMessage(role=role, content=content)  # type: ignore[arg-type]


def test_classify_short_neutral_message_is_standard() -> None:
    history = [_msg("user", "Hallo")]
    assert classify_complexity(history) == "standard"


def test_classify_complex_keyword_triggers_complex() -> None:
    history = [_msg("user", "Welcher Schuh passt für mich?")]
    assert classify_complexity(history) == "complex"


def test_classify_long_history_triggers_complex() -> None:
    long = "x" * 5000
    history = [_msg("user", long)]
    assert classify_complexity(history) == "complex"


def test_classify_english_keyword_triggers_complex() -> None:
    history = [_msg("user", "Can you recommend a running shoe?")]
    assert classify_complexity(history) == "complex"


async def test_router_uses_first_working_provider() -> None:
    primary = MockProvider(response="from primary")
    fallback = MockProvider(response="from fallback")
    router = Router(
        providers={"a": primary, "b": fallback},
        chains={"standard": ["a", "b"], "complex": ["a", "b"]},
    )
    result = await router.complete("sys", [_msg("user", "hi")])
    assert result.text == "from primary"
    assert len(primary.calls) == 1
    assert len(fallback.calls) == 0


async def test_router_falls_back_when_primary_raises() -> None:
    failing = MockProvider(raise_error=True)
    fallback = MockProvider(response="from fallback")
    router = Router(
        providers={"a": failing, "b": fallback},
        chains={"standard": ["a", "b"], "complex": ["a", "b"]},
    )
    result = await router.complete("sys", [_msg("user", "hi")])
    assert result.text == "from fallback"


async def test_router_raises_when_whole_chain_fails() -> None:
    failing1 = MockProvider(raise_error=True)
    failing2 = MockProvider(raise_error=True)
    router = Router(
        providers={"a": failing1, "b": failing2},
        chains={"standard": ["a", "b"], "complex": ["a", "b"]},
    )
    with pytest.raises(AllProvidersFailedError):
        await router.complete("sys", [_msg("user", "hi")])


async def test_router_skips_unknown_provider_ids() -> None:
    real = MockProvider(response="real")
    router = Router(
        providers={"real": real},
        chains={"standard": ["ghost", "real"], "complex": ["real"]},
    )
    result = await router.complete("sys", [_msg("user", "hi")])
    assert result.text == "real"
