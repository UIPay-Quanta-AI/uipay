import inspect

import pytest
from pydantic import ValidationError

from app.providers.tts import (
    TTSProvider,
    TTSProviderError,
    TTSResult,
)


class MockTTSProvider(TTSProvider):
    async def synthesize(
        self,
        *,
        text: str,
        voice: str | None = None,
        language: str | None = None,
    ) -> TTSResult:
        return TTSResult(
            audio=b"fake-audio",
            content_type="audio/mpeg",
            duration_seconds=2.1,
        )


def test_tts_result():
    result = TTSResult(
        audio=b"audio-data",
        content_type="audio/mpeg",
        duration_seconds=2.1,
    )

    assert result.audio == b"audio-data"
    assert result.content_type == "audio/mpeg"
    assert result.duration_seconds == 2.1


def test_tts_content_type_is_required():
    with pytest.raises(ValidationError):
        TTSResult(
            audio=b"audio-data",
            content_type="",
        )


def test_tts_duration_cannot_be_negative():
    with pytest.raises(ValidationError):
        TTSResult(
            audio=b"audio-data",
            content_type="audio/mpeg",
            duration_seconds=-1,
        )


@pytest.mark.asyncio
async def test_tts_provider_contract():
    provider = MockTTSProvider()

    result = await provider.synthesize(
        text="Your transfer was successful.",
        voice="default",
        language="en-NG",
    )

    assert isinstance(result, TTSResult)
    assert result.audio == b"fake-audio"
    assert result.content_type == "audio/mpeg"


def test_tts_provider_error():
    error = TTSProviderError("Speech synthesis failed.")

    assert isinstance(error, Exception)


def test_tts_provider_is_abstract():
    assert inspect.isabstract(TTSProvider)
