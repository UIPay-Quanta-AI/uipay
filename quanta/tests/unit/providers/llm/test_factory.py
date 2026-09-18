from app.core.config import Settings
from app.providers.llm.claude import ClaudeProvider
from app.providers.llm.factory import build_llm_provider
from app.providers.llm.groq import GroqProvider


def test_factory_builds_groq_provider():
    settings = Settings(
        LLM_PROVIDER="groq",
        GROQ_API_KEY="test-key",
    )

    provider = build_llm_provider(settings=settings)

    assert isinstance(provider, GroqProvider)


def test_factory_builds_claude_provider():
    settings = Settings(
        LLM_PROVIDER="claude",
        ANTHROPIC_API_KEY="test-key",
    )

    provider = build_llm_provider(settings=settings)

    assert isinstance(provider, ClaudeProvider)


def test_factory_rejects_unknown_provider():
    settings = Settings(
        LLM_PROVIDER="unknown",
    )

    try:
        build_llm_provider(settings=settings)
    except ValueError as exc:
        assert "Unsupported runtime LLM provider" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
