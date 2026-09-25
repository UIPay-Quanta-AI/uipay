from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings as default_settings
from app.providers.tts.base import TTSConfigurationError, TTSProvider
from app.providers.tts.edge import EdgeTTSProvider
from app.providers.tts.naijalingo import NaijaLingoProvider

if TYPE_CHECKING:
    from app.core.config import Settings


def get_tts_provider(
    provider_name: str | None = None,
    settings: Settings | None = None,
) -> TTSProvider:
    """
    Factory function returning the configured TTSProvider instance.

    Supported provider names: 'edge', 'naijalingo' (or '9jalingo').
    Raises TTSConfigurationError if provider_name is unknown.
    """
    s = settings or default_settings
    raw_name = provider_name or s.TTS_PROVIDER
    name = (raw_name or "").strip().lower()

    if name == "edge":
        return EdgeTTSProvider()

    if name in {"naijalingo", "9jalingo"}:
        return NaijaLingoProvider(
            api_key=s.NAIJALINGO_API_KEY,
            settings=s,
        )

    raise TTSConfigurationError(
        f"Unsupported TTS provider '{raw_name}'. Supported providers are 'edge' and 'naijalingo'."
    )
