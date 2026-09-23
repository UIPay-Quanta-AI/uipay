import io
from unittest.mock import MagicMock

import pytest
from PIL import Image

from app.providers.ocr import OCRProvider, OCRResult, PaddleOCRProvider


def _make_test_image() -> bytes:
    img = Image.new("RGB", (200, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class MockPaddle3xResult:
    def __init__(self, text: str, score: float = 0.98) -> None:
        self.rec_texts = [text]
        self.rec_scores = [score]
        self.dt_polys = [[[10, 10], [90, 10], [90, 30], [10, 30]]]


@pytest.mark.asyncio
async def test_paddleocr_provider_conforms_to_ocr_provider_contract():
    mock_pipeline = MagicMock()
    mock_pipeline.predict.return_value = [MockPaddle3xResult("Account: 0123456789")]

    provider: OCRProvider = PaddleOCRProvider(device="cpu", pipeline=mock_pipeline)

    result = await provider.extract(
        image=_make_test_image(),
        filename="bank_statement.png",
    )

    # Contract verifications
    assert isinstance(result, OCRResult)
    assert isinstance(result.text, str)
    assert len(result.text) > 0
    assert result.text == "Account: 0123456789"
    assert isinstance(result.blocks, list)
    assert len(result.blocks) == 1
    assert result.blocks[0].text == "Account: 0123456789"
    assert result.blocks[0].confidence == 0.98
    assert result.provider == "paddleocr"
    assert "device" in result.provider_metadata
    assert "elapsed_seconds" in result.provider_metadata
