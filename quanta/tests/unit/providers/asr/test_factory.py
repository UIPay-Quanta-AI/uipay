from __future__ import annotations

import pytest

from app.core.config import Settings
from app.providers.asr import (
    ASRConfigurationError,
    FasterWhisperProvider,
    NaijaVoxProvider,
    get_asr_provider,
)


def test_factory_returns_naijavox_provider():
    settings = Settings(ASR_PROVIDER="naijavox")
    provider = get_asr_provider(settings=settings)

    assert isinstance(provider, NaijaVoxProvider)
    assert provider.model_id == "Axiveri/NaijaVox-2.0"


def test_factory_returns_faster_whisper_provider():
    settings = Settings(ASR_PROVIDER="faster_whisper")
    provider = get_asr_provider(settings=settings)

    assert isinstance(provider, FasterWhisperProvider)
    assert provider.model_name == "large-v3"


def test_factory_accepts_explicit_provider_override():
    settings = Settings(ASR_PROVIDER="naijavox")
    provider = get_asr_provider(provider_name="faster-whisper", settings=settings)

    assert isinstance(provider, FasterWhisperProvider)


def test_factory_unknown_provider_raises_configuration_error():
    with pytest.raises(ASRConfigurationError, match="Unsupported ASR provider"):
        get_asr_provider(provider_name="invalid_engine")
