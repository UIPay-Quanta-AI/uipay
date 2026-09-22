from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.providers.asr import (
    ASRConfigurationError,
    ASRError,
    ASRInputError,
    ASRModelLoadError,
    ASRProviderError,
    ASRResult,
    ASRTranscriptionError,
    normalize_language,
)
from app.providers.base import ProviderError


def test_normalize_language_canonical_codes():
    assert normalize_language("en") == "en"
    assert normalize_language("pcm") == "pcm"
    assert normalize_language("yo") == "yo"
    assert normalize_language("ha") == "ha"
    assert normalize_language("ig") == "ig"


def test_normalize_language_aliases():
    assert normalize_language("english") == "en"
    assert normalize_language("Nigerian English") == "en"
    assert normalize_language("pidgin") == "pcm"
    assert normalize_language("Nigerian Pidgin") == "pcm"
    assert normalize_language("Yoruba") == "yo"
    assert normalize_language("Hausa") == "ha"
    assert normalize_language("Igbo") == "ig"


def test_normalize_language_none_or_empty():
    assert normalize_language(None) is None
    assert normalize_language("") is None
    assert normalize_language("   ") is None


def test_normalize_language_unsupported_raises_input_error():
    with pytest.raises(ASRInputError, match="Unsupported language"):
        normalize_language("swahili")


def test_asr_result_fields_and_aliases():
    result = ASRResult(
        text="Send 5000 naira to Mum.",
        language="pcm",
        confidence=0.92,
        duration_seconds=3.5,
        provider="naijavox",
        provider_metadata={"model": "Axiveri/NaijaVox-2.0"},
    )

    assert result.text == "Send 5000 naira to Mum."
    assert result.language == "pcm"
    assert result.confidence == 0.92
    assert result.duration_seconds == 3.5
    assert result.provider == "naijavox"
    assert result.metadata == {"model": "Axiveri/NaijaVox-2.0"}
    assert result.provider_metadata == {"model": "Axiveri/NaijaVox-2.0"}


def test_asr_result_validations():
    with pytest.raises(ValidationError):
        ASRResult(text="")

    with pytest.raises(ValidationError):
        ASRResult(text="Valid", confidence=1.2)

    with pytest.raises(ValidationError):
        ASRResult(text="Valid", duration_seconds=-0.5)


def test_error_hierarchy():
    base_err = ASRError("base")
    config_err = ASRConfigurationError("config")
    input_err = ASRInputError("input")
    provider_err = ASRProviderError("provider")
    load_err = ASRModelLoadError("load")
    trans_err = ASRTranscriptionError("transcription")

    assert isinstance(base_err, ProviderError)
    assert isinstance(config_err, ASRError)
    assert isinstance(input_err, ASRError)
    assert isinstance(provider_err, ASRError)
    assert isinstance(load_err, ASRProviderError)
    assert isinstance(trans_err, ASRProviderError)
