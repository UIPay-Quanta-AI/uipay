import inspect

import pytest
from pydantic import ValidationError

from app.providers.asr import (
    ASRProvider,
    ASRProviderError,
    ASRResult,
)


class MockASRProvider(ASRProvider):
    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str | None = None,
        language: str | None = None,
    ) -> ASRResult:
        return ASRResult(
            text="Send five thousand naira to Amaka.",
            language=language or "en-NG",
            confidence=0.95,
            duration_seconds=3.2,
        )


def test_asr_result():
    result = ASRResult(
        text="Send five thousand naira.",
        language="en-NG",
        confidence=0.95,
        duration_seconds=2.5,
    )

    assert result.text == "Send five thousand naira."
    assert result.language == "en-NG"
    assert result.confidence == 0.95
    assert result.duration_seconds == 2.5


def test_asr_result_rejects_empty_text():
    with pytest.raises(ValidationError):
        ASRResult(text="")


def test_asr_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValidationError):
        ASRResult(
            text="Hello.",
            confidence=1.5,
        )


def test_asr_duration_cannot_be_negative():
    with pytest.raises(ValidationError):
        ASRResult(
            text="Hello.",
            duration_seconds=-1,
        )


@pytest.mark.asyncio
async def test_asr_provider_contract():
    provider = MockASRProvider()

    result = await provider.transcribe(
        audio=b"fake-audio",
        filename="voice.webm",
        language="en-NG",
    )

    assert isinstance(result, ASRResult)
    assert result.text == "Send five thousand naira to Amaka."
    assert result.language == "en-NG"


def test_asr_provider_error():
    error = ASRProviderError("Transcription failed.")

    assert isinstance(error, Exception)


def test_asr_provider_is_abstract():
    assert inspect.isabstract(ASRProvider)
