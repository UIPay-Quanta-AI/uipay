from __future__ import annotations

from abc import abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.providers.base import Provider, ProviderError

# ---------------------------------------------------------------------------
# Error Hierarchy
# ---------------------------------------------------------------------------


class OCRError(ProviderError):
    """
    Base exception for all OCR subsystem errors.
    """


class OCRConfigurationError(OCRError):
    """
    Raised when OCR configuration (provider, device, limits) is invalid.
    """


class OCRInputError(OCRError):
    """
    Raised when the input image is invalid, empty, unsupported, or oversized.
    """


class OCRProviderError(OCRError):
    """
    Raised when an OCR provider fails during model execution.

    Kept as a direct subclass of OCRError (not OCRModelLoadError/OCRExtractionError)
    so existing code that catches OCRProviderError continues to work correctly.
    """


class OCRModelLoadError(OCRProviderError):
    """
    Raised when an OCR model or its dependencies fail to load or initialize.
    """


class OCRExtractionError(OCRProviderError):
    """
    Raised when a text-extraction inference operation fails.
    """


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class OCRTextBlock(BaseModel):
    """
    A normalized OCR text segment representing one detected text region.

    bbox stores the four-corner polygon returned by PaddleOCR, preserved as-is
    so that downstream semantic extraction can reconstruct reading order or
    spatial relationships if needed.  Each inner list is [x, y].

    Example bbox (four corners, clockwise from top-left):
        [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
    """

    text: str = Field(min_length=1)
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    # Four-corner polygon or None when the provider cannot supply position.
    # Stored as [[x0,y0],[x1,y1],[x2,y2],[x3,y3]] (PaddleOCR native shape).
    bbox: list[list[float]] | None = Field(default=None)


class OCRResult(BaseModel):
    """
    Provider-neutral OCR result.

    text       – Full extracted text joined from all blocks, with meaningful
                 line breaks preserved.  This is the primary field for semantic
                 extraction; Claude should read this.
    blocks     – Individual detected text regions ordered for reading.
    provider   – Identifier of the provider that produced this result.
    provider_metadata – Safe diagnostic metadata (model, device, language).
                        Downstream code must NOT rely on provider-specific keys.
    """

    text: str = Field(min_length=1)
    blocks: list[OCRTextBlock] = Field(default_factory=list)
    provider: str = Field(default="unknown")
    provider_metadata: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract Interface
# ---------------------------------------------------------------------------


class OCRProvider(Provider):
    """
    Provider-neutral interface for optical character recognition.
    """

    @property
    def capabilities(self) -> dict[str, Any]:
        """
        Return informational provider/model capability metadata.
        """
        return {
            "provider": "unknown",
            "model": "unknown",
            "language_selection_supported": False,
            "auto_detection_supported": False,
            "supported_languages": [],
        }

    @abstractmethod
    async def extract(
        self,
        *,
        image: bytes,
        filename: str | None = None,
    ) -> OCRResult:
        """
        Extract text from an image.

        Parameters
        ----------
        image:
            Raw image bytes (PNG, JPEG, WebP, …).  The provider is responsible
            for validating and decoding these bytes.
        filename:
            Optional original filename, used only for logging / metadata.
            Must NOT be used as a filesystem path.

        Returns
        -------
        OCRResult
            Normalized, provider-neutral OCR output.
        """
        raise NotImplementedError
