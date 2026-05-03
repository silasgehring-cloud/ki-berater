"""Build the production Router from settings.

Real providers are only instantiated when their API key is configured.
Tests inject a router with the MockProvider via FastAPI dependency override.

Dev-only fallback: when NO API keys are set AND environment != production,
we register an in-process MockProvider so the End-to-End-Flow works without
external dependencies. In production this never kicks in — `llm.no_providers
_configured` warning fires and Router.complete() will raise.
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
        if settings.is_production:
            logger.warning(
                "llm.no_providers_configured",
                hint="set ANTHROPIC_API_KEY and/or GOOGLE_API_KEY",
            )
        else:
            # Dev fallback so the local end-to-end flow works without API keys.
            from backend.llm.providers.mock import MockProvider

            mock = MockProvider(
                response=(
                    "Hallo! Das ist eine Beispielantwort vom Mock-Provider, "
                    "weil aktuell kein echter LLM-Anbieter konfiguriert ist. "
                    "Setze GOOGLE_API_KEY oder ANTHROPIC_API_KEY in deiner .env "
                    "fuer echte KI-Antworten."
                )
            )
            providers["mock-flash"] = mock
            providers["mock-sonnet"] = mock
            logger.warning(
                "llm.dev_mock_fallback_active",
                hint="set ANTHROPIC_API_KEY and/or GOOGLE_API_KEY for real LLM",
            )
            dev_chains: dict[Complexity, list[str]] = {
                "standard": ["mock-flash"],
                "complex": ["mock-sonnet"],
            }
            return Router(providers=providers, chains=dev_chains)

    chains: dict[Complexity, list[str]] = {
        "standard": ["gemini-flash", "claude-haiku"],
        "complex": ["claude-sonnet", "gemini-pro", "claude-haiku"],
    }

    return Router(providers=providers, chains=chains)
