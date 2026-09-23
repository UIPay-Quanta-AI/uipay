import io
from typing import Any
from unittest.mock import MagicMock

import pytest
from PIL import Image

from app.providers.ocr.base import (
    OCRConfigurationError,
    OCRExtractionError,
    OCRInputError,
    OCRResult,
)
from app.providers.ocr.paddleocr import (
    PaddleOCRProvider,
    _blocks_to_text,
    _parse_paddle_result,
    resolve_paddle_device,
)


def _valid_image_bytes() -> bytes:
    img = Image.new("RGB", (100, 50), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class MockPaddle3xResult:
    """Mock for PaddleOCR 3.x attribute-based result object."""

    def __init__(
        self, texts: list[str], scores: list[float], polys: list[Any] | None = None
    ) -> None:
        self.rec_texts = texts
        self.rec_scores = scores
        self.dt_polys = polys or [[[0, 0], [10, 0], [10, 10], [0, 10]] for _ in texts]


def test_lazy_init_does_not_load_pipeline():
    provider = PaddleOCRProvider(device="cpu")
    assert provider._pipeline is None


def test_resolve_paddle_device_cpu():
    assert resolve_paddle_device("cpu") == "cpu"


def test_resolve_paddle_device_invalid():
    with pytest.raises(OCRConfigurationError, match="Invalid OCR_PADDLE_DEVICE"):
        resolve_paddle_device("invalid_device")


def test_parse_paddle_result_attr_shape():
    mock_res = MockPaddle3xResult(
        texts=["GTBank", "Account: 1234567890"],
        scores=[0.99, 0.95],
        polys=[
            [[0, 0], [50, 0], [50, 20], [0, 20]],
            [[0, 25], [100, 25], [100, 45], [0, 45]],
        ],
    )
    blocks = _parse_paddle_result([mock_res])

    assert len(blocks) == 2
    assert blocks[0].text == "GTBank"
    assert blocks[0].confidence == 0.99
    assert blocks[0].bbox == [[0.0, 0.0], [50.0, 0.0], [50.0, 20.0], [0.0, 20.0]]
    assert blocks[1].text == "Account: 1234567890"


def test_parse_paddle_result_dict_shape():
    raw_dict = [
        {
            "text": "Amount: N50,000.00",
            "score": 0.98,
            "box": [[10, 10], [90, 10], [90, 30], [10, 30]],
        }
    ]
    blocks = _parse_paddle_result(raw_dict)

    assert len(blocks) == 1
    assert blocks[0].text == "Amount: N50,000.00"
    assert blocks[0].confidence == 0.98
    assert blocks[0].bbox == [[10.0, 10.0], [90.0, 10.0], [90.0, 30.0], [10.0, 30.0]]


def test_parse_paddle_result_legacy_shape():
    legacy_raw = [
        [
            [[[0, 0], [40, 0], [40, 15], [0, 15]], ("SUCCESS", 0.99)],
            [[[0, 20], [80, 20], [80, 35], [0, 35]], ("Ref: 98765", 0.92)],
        ]
    ]
    blocks = _parse_paddle_result(legacy_raw)

    assert len(blocks) == 2
    assert blocks[0].text == "SUCCESS"
    assert blocks[1].text == "Ref: 98765"


def test_blocks_to_text_collapses_blank_lines():
    from app.providers.ocr.base import OCRTextBlock

    blocks = [
        OCRTextBlock(text="Header"),
        OCRTextBlock(text="Line 1"),
        OCRTextBlock(text="Line 2"),
    ]
    text = _blocks_to_text(blocks)
    assert text == "Header\nLine 1\nLine 2"


@pytest.mark.asyncio
async def test_extract_valid_image_with_mock_pipeline():
    mock_pipeline = MagicMock()
    mock_pipeline.predict.return_value = [
        MockPaddle3xResult(
            texts=["GTBank", "Account Number: 0123456789"],
            scores=[0.99, 0.97],
        )
    ]

    provider = PaddleOCRProvider(device="cpu", pipeline=mock_pipeline)
    result = await provider.extract(image=_valid_image_bytes(), filename="receipt.png")

    assert isinstance(result, OCRResult)
    assert "GTBank" in result.text
    assert "Account Number: 0123456789" in result.text
    assert len(result.blocks) == 2
    assert result.provider == "paddleocr"
    assert result.provider_metadata["filename"] == "receipt.png"
    assert result.provider_metadata["device"] == "cpu"


@pytest.mark.asyncio
async def test_extract_invalid_image_raises_input_error():
    mock_pipeline = MagicMock()
    provider = PaddleOCRProvider(device="cpu", pipeline=mock_pipeline)

    with pytest.raises(OCRInputError):
        await provider.extract(image=b"corrupt image bytes")

    # Pipeline predict should never be called for invalid images
    mock_pipeline.predict.assert_not_called()


@pytest.mark.asyncio
async def test_extract_no_text_found_raises_extraction_error():
    mock_pipeline = MagicMock()
    mock_pipeline.predict.return_value = []

    provider = PaddleOCRProvider(device="cpu", pipeline=mock_pipeline)
    with pytest.raises(OCRExtractionError, match="found no text"):
        await provider.extract(image=_valid_image_bytes())


@pytest.mark.asyncio
async def test_extract_inference_failure_raises_extraction_error():
    mock_pipeline = MagicMock()
    mock_pipeline.predict.side_effect = Exception("CUDA error or runtime failure")

    provider = PaddleOCRProvider(device="cpu", pipeline=mock_pipeline)
    with pytest.raises(OCRExtractionError, match="failed"):
        await provider.extract(image=_valid_image_bytes())
