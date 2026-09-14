from __future__ import annotations

from abc import abstractmethod

from pydantic import BaseModel, Field

from app.providers.base import Provider, ProviderError


class ASRResult(BaseModel):
    """
    Provider-neutral speech recognition result.
    """

    text: str = Field(min_length=1)
    language: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    duration_seconds: float | None = Field(
        default=None,
        ge=0.0,
    )
    provider_metadata: dict[str, str] = Field(default_factory=dict)


class ASRProviderError(ProviderError):
    """
    Raised when an ASR provider fails.
    """


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
