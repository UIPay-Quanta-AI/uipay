from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.tts import (
    EdgeTTSProvider,
    TTSProviderError,
    TTSResult,
)


@pytest.mark.asyncio
async def test_edge_provider_empty_text():
    provider = EdgeTTSProvider()
    with pytest.raises(TTSProviderError, match="Text cannot be empty"):
        await provider.synthesize(text="   ", voice="en-NG-EzinneNeural")


@pytest.mark.asyncio
async def test_edge_provider_synthesize_success():
    provider = EdgeTTSProvider()

    async def mock_stream_chunks():
        yield {"type": "audio", "data": b"audio-chunk-1"}
        yield {"type": "audio", "data": b"audio-chunk-2"}

    mock_communicate = AsyncMock()
    mock_communicate.stream = mock_stream_chunks

    with patch("edge_tts.Communicate", return_value=mock_communicate) as mock_comm_cls:
        result = await provider.synthesize(
            text="Your transfer was successful.",
            voice="en-NG-EzinneNeural",
            language="en-NG",
        )

        mock_comm_cls.assert_called_once_with(
            text="Your transfer was successful.",
            voice="en-NG-EzinneNeural",
        )

        assert isinstance(result, TTSResult)
        assert result.audio == b"audio-chunk-1audio-chunk-2"
        assert result.content_type == "audio/mpeg"
        assert result.provider_metadata["provider"] == "edge"
        assert result.provider_metadata["voice"] == "en-NG-EzinneNeural"


@pytest.mark.asyncio
async def test_edge_provider_error_handling():
    provider = EdgeTTSProvider()

    async def mock_error_stream():
        raise TTSProviderError("Connection closed")
        yield  # make it an async generator

    mock_communicate = MagicMock()
    mock_communicate.stream = mock_error_stream

    with (
        patch("edge_tts.Communicate", return_value=mock_communicate),
        pytest.raises(TTSProviderError, match="Edge TTS synthesis failed|Connection closed"),
    ):
        await provider.synthesize(
            text="Hello world",
            voice="en-NG-EzinneNeural",
        )
