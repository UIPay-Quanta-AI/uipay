from __future__ import annotations

from app.providers.tts.base import (
    TTSConfigurationError,
    TTSProvider,
    TTSProviderError,
    TTSResult,
)
from app.providers.tts.edge import EdgeTTSProvider
from app.providers.tts.factory import get_tts_provider
from app.providers.tts.naijalingo import NaijaLingoProvider
from app.providers.tts.voices import (
    DEFAULT_VOICES,
    VoiceSelection,
    resolve_voice,
)

__all__ = [
    "DEFAULT_VOICES",
    "EdgeTTSProvider",
    "NaijaLingoProvider",
    "TTSConfigurationError",
    "TTSProvider",
    "TTSProviderError",
    "TTSResult",
    "VoiceSelection",
    "get_tts_provider",
    "resolve_voice",
]
