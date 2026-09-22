from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings as default_settings
from app.providers.asr.base import ASRConfigurationError, ASRProvider
from app.providers.asr.faster_whisper import FasterWhisperProvider
from app.providers.asr.naijavox import NaijaVoxProvider

if TYPE_CHECKING:
    from app.core.config import Settings


def get_asr_provider(
    provider_name: str | None = None,
    settings: Settings | None = None,
) -> ASRProvider:
    """
    Factory function returning the configured ASRProvider instance.

    Supported provider names: 'naijavox', 'faster_whisper' (or 'faster-whisper').
    Raises ASRConfigurationError if provider_name is unknown.
    """
    s = settings or default_settings
    name = (provider_name or s.ASR_PROVIDER).strip().lower()

    if name in {"naijavox", "naija-vox"}:
        return NaijaVoxProvider(
            model_id=s.ASR_NAIJAVOX_MODEL_ID,
            device=s.ASR_NAIJAVOX_DEVICE,
            max_audio_bytes=s.ASR_MAX_AUDIO_BYTES,
            max_duration_seconds=s.ASR_MAX_DURATION_SECONDS,
        )

    if name in {"faster_whisper", "faster-whisper", "fasterwhisper"}:
        return FasterWhisperProvider(
            model=s.ASR_FASTER_WHISPER_MODEL,
            device=s.ASR_FASTER_WHISPER_DEVICE,
            compute_type=s.ASR_FASTER_WHISPER_COMPUTE_TYPE,
            max_audio_bytes=s.ASR_MAX_AUDIO_BYTES,
            max_duration_seconds=s.ASR_MAX_DURATION_SECONDS,
        )

    raise ASRConfigurationError(
        f"Unsupported ASR provider '{provider_name or s.ASR_PROVIDER}'. "
        f"Supported providers are 'naijavox' and 'faster_whisper'."
    )
