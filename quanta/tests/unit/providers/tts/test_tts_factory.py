import pytest

from app.core.config import Settings
from app.providers.tts import (
    EdgeTTSProvider,
    NaijaLingoProvider,
    TTSConfigurationError,
    get_tts_provider,
)


def test_factory_get_edge_provider():
    provider = get_tts_provider(provider_name="edge")
    assert isinstance(provider, EdgeTTSProvider)


def test_factory_get_naijalingo_provider():
    custom_settings = Settings(NAIJALINGO_API_KEY="test_key")
    provider = get_tts_provider(provider_name="naijalingo", settings=custom_settings)
    assert isinstance(provider, NaijaLingoProvider)


def test_factory_get_9jalingo_alias():
    custom_settings = Settings(NAIJALINGO_API_KEY="test_key")
    provider = get_tts_provider(provider_name="9jalingo", settings=custom_settings)
    assert isinstance(provider, NaijaLingoProvider)


def test_factory_unsupported_provider():
    with pytest.raises(TTSConfigurationError, match="Unsupported TTS provider"):
        get_tts_provider(provider_name="unknown_provider")
