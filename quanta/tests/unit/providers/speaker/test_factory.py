from __future__ import annotations

import pytest

from app.core.config import Settings
from app.providers.speaker import SpeakerConfigurationError, get_speaker_provider
from app.providers.speaker.eagle import EagleProvider


def test_factory_returns_eagle_provider():
    settings = Settings(SPEAKER_PROVIDER="eagle", PICOVOICE_ACCESS_KEY="test-key")
    provider = get_speaker_provider(settings=settings)

    assert isinstance(provider, EagleProvider)
    assert provider.access_key == "test-key"
    assert provider.verification_threshold == settings.SPEAKER_VERIFICATION_THRESHOLD


def test_factory_accepts_explicit_provider_override():
    settings = Settings(SPEAKER_PROVIDER="eagle", PICOVOICE_ACCESS_KEY="test-key")
    provider = get_speaker_provider(provider_name="eagle", settings=settings)

    assert isinstance(provider, EagleProvider)


def test_factory_unknown_provider_raises_configuration_error():
    with pytest.raises(SpeakerConfigurationError, match="Unsupported speaker-verification provider"):
        get_speaker_provider(provider_name="invalid_engine", settings=Settings(PICOVOICE_ACCESS_KEY="k"))


def test_factory_missing_access_key_raises_configuration_error():
    settings = Settings(SPEAKER_PROVIDER="eagle", PICOVOICE_ACCESS_KEY=None)

    with pytest.raises(SpeakerConfigurationError, match="PICOVOICE_ACCESS_KEY"):
        get_speaker_provider(settings=settings)
