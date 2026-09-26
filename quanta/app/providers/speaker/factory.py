from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings as default_settings
from app.providers.speaker.base import SpeakerConfigurationError, SpeakerProvider
from app.providers.speaker.eagle import EagleProvider

if TYPE_CHECKING:
    from app.core.config import Settings


def get_speaker_provider(
    provider_name: str | None = None,
    settings: Settings | None = None,
) -> SpeakerProvider:
    """
    Factory function returning the configured SpeakerProvider instance.

    Supported provider names: 'eagle'.
    Raises SpeakerConfigurationError if provider_name is unknown.
    """
    s = settings or default_settings
    name = (provider_name or s.SPEAKER_PROVIDER).strip().lower()

    if name == "eagle":
        return EagleProvider(
            access_key=s.PICOVOICE_ACCESS_KEY,
            verification_threshold=s.SPEAKER_VERIFICATION_THRESHOLD,
            max_audio_bytes=s.SPEAKER_MAX_AUDIO_BYTES,
            max_duration_seconds=s.SPEAKER_MAX_DURATION_SECONDS,
        )

    raise SpeakerConfigurationError(
        f"Unsupported speaker-verification provider '{provider_name or s.SPEAKER_PROVIDER}'. "
        f"Supported providers are 'eagle'."
    )
