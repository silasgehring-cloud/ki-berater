"""Build the production Router from settings.

Real providers are only instantiated when their API key is configured.
Tests inject a router with the MockProvider via FastAPI dependency override.
"""
from __future__ import annotations

import structlog

from backend.core.config import settings
from backend.llm.providers.base import LLMProvider
from backend.llm.router import Complexity, Router

logger = structlog.get_logger("backend.llm.bootstrap")


def build_default_router() -> Router:
    providers: dict[str, LLMProvider] = {}

    if settings.google_api_key:
        from backend.llm.providers.google import GoogleProvider

        providers["gemini-flash"] = GoogleProvider(
            api_key=settings.google_api_key, model_id="gemini-2.5-flash"
        )
        providers["gemini-pro"] = GoogleProvider(
            api_key=settings.google_api_key, model_id="gemini-2.5-pro"
        )

    if settings.anthropic_api_key:
        from backend.llm.providers.anthropic import AnthropicProvider

        providers["claude-sonnet"] = AnthropicProvider(
            api_key=settings.anthropic_api_key, model_id="claude-sonnet-4-5"
        )
        providers["claude-haiku"] = AnthropicProvider(
            api_key=settings.anthropic_api_key, model_id="claude-haiku-4-5"
        )

    if not providers:
        logger.warning(
            "llm.no_providers_configured",
            hint="set ANTHROPIC_API_KEY and/or GOOGLE_API_KEY",
        )

    chains: dict[Complexity, list[str]] = {
        "standard": ["gemini-flash", "claude-haiku"],
        "complex": ["claude-sonnet", "gemini-pro", "claude-haiku"],
    }

    return Router(providers=providers, chains=chains)
