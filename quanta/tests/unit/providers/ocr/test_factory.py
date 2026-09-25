import pytest

from app.core.config import Settings
from app.providers.ocr import OCRConfigurationError, PaddleOCRProvider, get_ocr_provider


def test_get_ocr_provider_paddleocr_explicit():
    provider = get_ocr_provider("paddleocr")
    assert isinstance(provider, PaddleOCRProvider)
    assert provider._pipeline is None


def test_get_ocr_provider_default():
    provider = get_ocr_provider()
    assert isinstance(provider, PaddleOCRProvider)
    assert provider._pipeline is None


def test_get_ocr_provider_case_insensitive():
    provider = get_ocr_provider("PaddleOCR")
    assert isinstance(provider, PaddleOCRProvider)


def test_get_ocr_provider_unknown_raises_configuration_error():
    with pytest.raises(OCRConfigurationError, match="Unsupported OCR provider 'tesseract'"):
        get_ocr_provider("tesseract")


def test_get_ocr_provider_custom_settings():
    custom_settings = Settings(
        OCR_PROVIDER="paddleocr",
        OCR_PADDLE_DEVICE="cpu",
        OCR_MAX_IMAGE_BYTES=5_000_000,
        OCR_MAX_IMAGE_PIXELS=10_000_000,
    )

    provider = get_ocr_provider(settings=custom_settings)
    assert isinstance(provider, PaddleOCRProvider)
    assert provider.device_setting == "cpu"
    assert provider.max_image_bytes == 5_000_000
    assert provider.max_image_pixels == 10_000_000
