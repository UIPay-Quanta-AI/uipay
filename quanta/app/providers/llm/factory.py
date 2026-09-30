from __future__ import annotations

from app.core.config import Settings
from app.core.config import settings as default_settings
from app.providers.llm.base import LLMProvider
from app.providers.llm.groq import GroqProvider


def build_llm_provider(
    *,
    settings: Settings,
) -> LLMProvider:
    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name == "groq":
        return GroqProvider(settings=settings)

    if provider_name == "claude":
        from app.providers.llm.claude import ClaudeProvider

        return ClaudeProvider(settings=settings)

    raise ValueError(f"Unsupported runtime LLM provider: {settings.LLM_PROVIDER}")


def get_llm_provider(
    settings: Settings | None = None,
) -> LLMProvider:
    return build_llm_provider(settings=settings or default_settings)
