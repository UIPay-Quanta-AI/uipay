import inspect

import pytest
from pydantic import ValidationError

from app.providers.ocr import (
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
        )


def test_ocr_text_block():
    block = OCRTextBlock(
        text="Account Number: 0123456789",
        confidence=0.97,
    )

    assert block.text == "Account Number: 0123456789"
    assert block.confidence == 0.97


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


def test_ocr_provider_error():
    error = OCRProviderError("OCR failed.")

    assert isinstance(error, Exception)


def test_ocr_provider_is_abstract():
    assert inspect.isabstract(OCRProvider)
