"""
Multilingual regression test suite verifying canonical language code handling (en, pcm, ig, yo, ha).
"""

from __future__ import annotations

from app.core.context import RequestContext, normalize_locale
from app.orchestration.orchestrator import resolve_effective_response_language
from app.providers.llm.base import LLMResponse


def test_canonical_locale_normalization():
    """Verify that all locale inputs normalize to canonical codes: en, pcm, ig, yo, ha."""
    assert normalize_locale("en") == "en"
    assert normalize_locale("en-NG") == "en"
    assert normalize_locale("en_NG") == "en"
    assert normalize_locale("nigerian english") == "en"

    assert normalize_locale("pcm") == "pcm"
    assert normalize_locale("pidgin") == "pcm"
    assert normalize_locale("nigerian_pidgin") == "pcm"

    assert normalize_locale("ig") == "ig"
    assert normalize_locale("igbo") == "ig"

    assert normalize_locale("yo") == "yo"
    assert normalize_locale("yoruba") == "yo"

    assert normalize_locale("ha") == "ha"
    assert normalize_locale("hausa") == "ha"

    # Unknown locale falls back cleanly to 'en'
    assert normalize_locale("unknown_lang") == "en"
    assert normalize_locale(None) == "en"


def test_effective_response_language_resolution():
    """Verify effective response language resolution across LLM provider metadata and RequestContext."""
    ctx_pcm = RequestContext.create(user_id="u1", session_id="s1", operation="TEXT", locale="pcm")

    # Fallback to RequestContext locale when LLM metadata is absent
    assert resolve_effective_response_language(ctx_pcm, None) == "pcm"

    # LLM explicit metadata overrides context locale if canonical
    llm_resp = LLMResponse(
        text="Abeg look this transfer",
        provider_metadata={"response_language": "pcm"},
    )
    assert resolve_effective_response_language(ctx_pcm, llm_resp) == "pcm"

    # Non-canonical metadata falls back to context locale
    llm_invalid = LLMResponse(
        text="Hello",
        provider_metadata={"response_language": "invalid_code"},
    )
    assert resolve_effective_response_language(ctx_pcm, llm_invalid) == "pcm"


from app.providers.tts.voices import resolve_voice


def test_tts_voice_id_mapping_for_all_canonical_languages():
    """Verify TTS voice resolution maps canonical language codes to correct provider voices."""
    v_en = resolve_voice("en")
    assert "en-NG" in v_en.voice or "Ezinne" in v_en.voice or "Abeo" in v_en.voice

    v_pcm = resolve_voice("pcm")
    assert (
        "pcm" in v_pcm.voice.lower()
        or "dora" in v_pcm.voice.lower()
        or "frank" in v_pcm.voice.lower()
    )

    v_ig = resolve_voice("ig")
    assert "ig" in v_ig.voice.lower() or "obianuju" in v_ig.voice.lower()

    v_yo = resolve_voice("yo")
    assert "yo" in v_yo.voice.lower() or "abisoye" in v_yo.voice.lower()

    v_ha = resolve_voice("ha")
    assert "ha" in v_ha.voice.lower() or "maryam" in v_ha.voice.lower()
