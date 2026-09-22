from __future__ import annotations

from abc import abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.providers.base import Provider, ProviderError

# ---------------------------------------------------------------------------
# Supported Languages & Normalization
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES: set[str] = {"en", "pcm", "yo", "ha", "ig"}

LANGUAGE_ALIASES: dict[str, str] = {
    "english": "en",
    "nigerian_english": "en",
    "nigerian english": "en",
    "en-ng": "en",
    "en_ng": "en",
    "pidgin": "pcm",
    "nigerian_pidgin": "pcm",
    "nigerian pidgin": "pcm",
    "yoruba": "yo",
    "hausa": "ha",
    "igbo": "ig",
}


# ---------------------------------------------------------------------------
# Error Hierarchy
# ---------------------------------------------------------------------------


class ASRError(ProviderError):
    """
    Base exception for all ASR subsystem errors.
    """


class ASRConfigurationError(ASRError):
    """
    Raised when ASR configuration or device specification is invalid.
    """


class ASRInputError(ASRError):
    """
    Raised when input audio or parameters are invalid.
    """


class ASRProviderError(ASRError):
    """
    Raised when an ASR provider fails during model execution.
    """


class ASRModelLoadError(ASRProviderError):
    """
    Raised when an ASR model or processor fails to load.
    """


class ASRTranscriptionError(ASRProviderError):
    """
    Raised when an ASR transcription operation fails.
    """


def normalize_language(language: str | None) -> str | None:
    """
    Normalize language input to canonical code (en, pcm, yo, ha, ig).

    Raises ASRInputError if language is unsupported.
    """
    if language is None:
        return None
    cleaned = language.strip().lower()
    if not cleaned:
        return None
    if cleaned in SUPPORTED_LANGUAGES:
        return cleaned
    if cleaned in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[cleaned]
    raise ASRInputError(
        f"Unsupported language '{language}'. Supported language codes: "
        f"{', '.join(sorted(SUPPORTED_LANGUAGES))}"
    )


# ---------------------------------------------------------------------------
# Models & Contract
# ---------------------------------------------------------------------------


class ASRResult(BaseModel):
    """
    Provider-neutral speech recognition result.
    """

    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(min_length=1)
    language: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    duration_seconds: float | None = Field(default=None, ge=0.0)
    provider: str = Field(default="unknown")
    metadata: dict[str, Any] = Field(default_factory=dict, alias="provider_metadata")

    @property
    def provider_metadata(self) -> dict[str, Any]:
        return self.metadata


class ASRProvider(Provider):
    """
    Provider-neutral interface for automatic speech recognition.
    """

    @abstractmethod
    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str | None = None,
        language: str | None = None,
    ) -> ASRResult:
        """
        Transcribe audio and return normalized speech recognition output.
        """
        raise NotImplementedError
