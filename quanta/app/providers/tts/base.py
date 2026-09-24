from __future__ import annotations

from abc import abstractmethod

from pydantic import BaseModel, Field

from app.providers.base import Provider, ProviderError


class TTSResult(BaseModel):
    """
    Provider-neutral text-to-speech result.
    """

    audio: bytes
    content_type: str = Field(min_length=1)
    duration_seconds: float | None = Field(
        default=None,
        ge=0.0,
    )
    provider_metadata: dict[str, str] = Field(default_factory=dict)


class TTSProviderError(ProviderError):
    """
    Raised when a TTS provider fails.
    """


class TTSConfigurationError(TTSProviderError):
    """
    Raised when TTS provider configuration is invalid or unsupported.
    """


class TTSProvider(Provider):
    """
    Provider-neutral interface for text-to-speech providers.
    """

    @abstractmethod
    async def synthesize(
        self,
        *,
        text: str,
        voice: str | None = None,
        language: str | None = None,
    ) -> TTSResult:
        """
        Convert text into speech.
        """
        raise NotImplementedError
