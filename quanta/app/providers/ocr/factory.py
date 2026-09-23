from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings as default_settings
from app.providers.ocr.base import OCRConfigurationError, OCRProvider
from app.providers.ocr.paddleocr import PaddleOCRProvider

if TYPE_CHECKING:
    from app.core.config import Settings


def get_ocr_provider(
    provider_name: str | None = None,
    settings: Settings | None = None,
) -> OCRProvider:
    """
    Factory function returning the configured OCRProvider instance.

    Supported provider names: 'paddleocr'.
    Raises OCRConfigurationError if provider_name is unknown.

    The returned provider is lightweight — no models are downloaded or
    initialised at construction time.  Initialisation is deferred to the
    first extract() call.
    """
    s = settings or default_settings
    name = (provider_name or s.OCR_PROVIDER).strip().lower()

    if name == "paddleocr":
        return PaddleOCRProvider(
            device=s.OCR_PADDLE_DEVICE,
            max_image_bytes=s.OCR_MAX_IMAGE_BYTES,
            max_image_pixels=s.OCR_MAX_IMAGE_PIXELS,
        )

    raise OCRConfigurationError(
        f"Unsupported OCR provider '{provider_name or s.OCR_PROVIDER}'. "
        "Supported providers: 'paddleocr'."
    )
