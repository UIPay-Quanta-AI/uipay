from __future__ import annotations

from app.core.context import RequestContext
from app.providers.asr.base import SUPPORTED_LANGUAGES, normalize_language
from app.providers.asr.naijavox import NAIJAVOX_TOKEN_MAP
from app.providers.ocr.paddleocr import PaddleOCRProvider
from app.providers.tts.voices import resolve_voice
from app.schemas.response import QuantaResponse


def test_canonical_supported_languages():
    expected = {"en", "pcm", "ig", "yo", "ha"}
    assert SUPPORTED_LANGUAGES == expected

    # Verify normalization for all 5 languages & aliases
    assert normalize_language("en") == "en"
    assert normalize_language("en-NG") == "en"
    assert normalize_language("nigerian_english") == "en"

    assert normalize_language("pcm") == "pcm"
    assert normalize_language("pidgin") == "pcm"

    assert normalize_language("ig") == "ig"
    assert normalize_language("igbo") == "ig"

    assert normalize_language("yo") == "yo"
    assert normalize_language("yoruba") == "yo"

    assert normalize_language("ha") == "ha"
    assert normalize_language("hausa") == "ha"


def test_request_context_locale_defaults_to_en_and_normalizes():
    # Default is 'en'
    ctx1 = RequestContext.create(user_id="user1", session_id="s1", operation="transfer")
    assert ctx1.locale == "en"

    # Supported language codes map directly
    for lang in ["en", "pcm", "ig", "yo", "ha"]:
        ctx = RequestContext.create(
            user_id="user1", session_id="s1", operation="transfer", locale=lang
        )
        assert ctx.locale == lang

    # Aliases normalize to canonical code
    assert (
        RequestContext.create(user_id="u", session_id="s", operation="t", locale="en-NG").locale
        == "en"
    )
    assert (
        RequestContext.create(user_id="u", session_id="s", operation="t", locale="igbo").locale
        == "ig"
    )
    assert (
        RequestContext.create(user_id="u", session_id="s", operation="t", locale="pcm-NG").locale
        == "pcm"
    )


def test_naijavox_language_token_mapping():
    # Verify exact 5 canonical tokens without regional suffixes
    assert NAIJAVOX_TOKEN_MAP["en"] == "<|en|>"
    assert NAIJAVOX_TOKEN_MAP["pcm"] == "<|pcm|>"
    assert NAIJAVOX_TOKEN_MAP["ig"] == "<|ig|>"
    assert NAIJAVOX_TOKEN_MAP["yo"] == "<|yo|>"
    assert NAIJAVOX_TOKEN_MAP["ha"] == "<|ha|>"

    for token in NAIJAVOX_TOKEN_MAP.values():
        assert "-NG" not in token
        assert "_NG" not in token


def test_ocr_provider_capabilities_metadata():
    provider = PaddleOCRProvider(device="cpu")
    caps = provider.capabilities

    assert caps["provider"] == "paddleocr"
    assert caps["model"] == "PP-OCRv6_medium"
    assert caps["language_selection_supported"] is False
    assert caps["auto_detection_supported"] is True
    assert "ch" in caps["supported_languages"]
    assert "en" in caps["supported_languages"]
    # ig, yo, ha, pcm are NOT in paddleocr's supported languages parameter
    assert "ig" not in caps["supported_languages"]
    assert "yo" not in caps["supported_languages"]


def test_tts_voice_resolution_and_decoupling():
    # Verify resolve_voice for all 5 languages
    en_voice = resolve_voice(language="en", gender="female")
    assert en_voice.provider == "edge"
    assert "Ezinne" in en_voice.voice

    ig_voice = resolve_voice(language="ig", gender="female")
    assert ig_voice.provider == "naijalingo"
    assert "obianuju_ig" in ig_voice.voice

    yo_voice = resolve_voice(language="yo", gender="female")
    assert yo_voice.provider == "naijalingo"
    assert "abisoye_yo" in yo_voice.voice

    ha_voice = resolve_voice(language="ha", gender="female")
    assert ha_voice.provider == "naijalingo"
    assert "maryam_ha" in ha_voice.voice

    pcm_voice = resolve_voice(language="pcm", gender="female")
    assert pcm_voice.provider == "naijalingo"
    assert "dora_pcm" in pcm_voice.voice

    # Decoupling check: RequestContext.locale = "ig", but LLM response_language = "en"
    ctx = RequestContext.create(user_id="u1", session_id="s1", operation="transfer", locale="ig")
    resp = QuantaResponse.success(
        request_id=ctx.request_id, speech_text="Done.", response_language="en"
    )

    # TTS service resolves using response.response_language, NOT context.locale
    selected = resolve_voice(language=resp.response_language, gender="female")
    assert selected.provider == "edge"
    assert "Ezinne" in selected.voice
