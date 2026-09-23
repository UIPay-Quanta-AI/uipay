import inspect

import pytest
from pydantic import ValidationError

from app.providers.ocr import (
    OCRConfigurationError,
    OCRError,
    OCRExtractionError,
    OCRInputError,
    OCRModelLoadError,
    OCRProvider,
    OCRProviderError,
    OCRResult,
    OCRTextBlock,
)


class MockOCRProvider(OCRProvider):
    async def extract(
        self,
        *,
        image: bytes,
        filename: str | None = None,
    ) -> OCRResult:
        return OCRResult(
            text=("GTBank\nAccount Number: 0123456789\nAccount Name: Amaka Okafor"),
            blocks=[
                OCRTextBlock(text="GTBank"),
                OCRTextBlock(text="Account Number: 0123456789"),
                OCRTextBlock(text="Account Name: Amaka Okafor"),
            ],
            provider="mock",
        )


def test_ocr_text_block():
    block = OCRTextBlock(
        text="Account Number: 0123456789",
        confidence=0.97,
    )

    assert block.text == "Account Number: 0123456789"
    assert block.confidence == 0.97
    assert block.bbox is None


def test_ocr_text_block_with_bbox():
    bbox = [[10.0, 10.0], [50.0, 10.0], [50.0, 30.0], [10.0, 30.0]]
    block = OCRTextBlock(
        text="GTBank",
        confidence=0.99,
        bbox=bbox,
    )

    assert block.text == "GTBank"
    assert block.bbox == bbox


def test_ocr_result():
    result = OCRResult(
        text="GTBank\nAccount Number: 0123456789",
        blocks=[
            OCRTextBlock(text="GTBank"),
            OCRTextBlock(text="Account Number: 0123456789"),
        ],
    )

    assert "GTBank" in result.text
    assert len(result.blocks) == 2
    assert result.provider == "unknown"


def test_ocr_result_rejects_empty_text():
    with pytest.raises(ValidationError):
        OCRResult(text="")


def test_ocr_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValidationError):
        OCRTextBlock(
            text="GTBank",
            confidence=-0.1,
        )


@pytest.mark.asyncio
async def test_ocr_provider_contract():
    provider = MockOCRProvider()

    result = await provider.extract(
        image=b"fake-image",
        filename="account.png",
    )

    assert isinstance(result, OCRResult)
    assert "GTBank" in result.text
    assert len(result.blocks) == 3
    assert result.provider == "mock"


def test_ocr_error_hierarchy():
    generic_err = OCRError("Generic OCR error")
    assert isinstance(generic_err, Exception)
    config_err = OCRConfigurationError("Bad config")
    input_err = OCRInputError("Bad image input")
    provider_err = OCRProviderError("Provider failed")
    load_err = OCRModelLoadError("Model failed to load")
    extraction_err = OCRExtractionError("Extraction failed")

    assert isinstance(config_err, OCRError)
    assert isinstance(input_err, OCRError)
    assert isinstance(provider_err, OCRError)
    assert isinstance(load_err, OCRProviderError)
    assert isinstance(load_err, OCRError)
    assert isinstance(extraction_err, OCRProviderError)
    assert isinstance(extraction_err, OCRError)


def test_ocr_provider_error():
    error = OCRProviderError("OCR failed.")
    assert isinstance(error, Exception)
    assert isinstance(error, OCRError)


def test_ocr_provider_is_abstract():
    assert inspect.isabstract(OCRProvider)
