from __future__ import annotations

from abc import abstractmethod

from pydantic import BaseModel, Field

from app.providers.base import Provider, ProviderError


class OCRTextBlock(BaseModel):
    """
    A normalized OCR text segment.
    """

    text: str = Field(min_length=1)
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class OCRResult(BaseModel):
    """
    Provider-neutral OCR result.
    """

    text: str = Field(min_length=1)
    blocks: list[OCRTextBlock] = Field(default_factory=list)
    provider_metadata: dict[str, str] = Field(default_factory=dict)


class OCRProviderError(ProviderError):
    """
    Raised when an OCR provider fails.
    """


class OCRProvider(Provider):
    """
    Provider-neutral interface for optical character recognition.
    """

    @abstractmethod
    async def extract(
        self,
        *,
        image: bytes,
        filename: str | None = None,
    ) -> OCRResult:
        """
        Extract text from an image.
        """
        raise NotImplementedError
