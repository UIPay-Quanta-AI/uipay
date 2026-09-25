from unittest.mock import MagicMock, patch

import pytest

from app.providers.tts import (
    NaijaLingoProvider,
    TTSConfigurationError,
    TTSProviderError,
    TTSResult,
)


def test_naijalingo_missing_api_key():
    provider = NaijaLingoProvider(api_key="")
    with pytest.raises(TTSConfigurationError, match="NAIJALINGO_API_KEY is missing"):
        provider._get_client()


@pytest.mark.asyncio
async def test_naijalingo_empty_text():
    provider = NaijaLingoProvider(api_key="test_key")
    with pytest.raises(TTSProviderError, match="Text cannot be empty"):
        await provider.synthesize(text="", voice="obianuju_ig", language="ig")


@pytest.mark.asyncio
async def test_naijalingo_missing_voice():
    provider = NaijaLingoProvider(api_key="test_key")
    with pytest.raises(TTSProviderError, match="Voice .* parameter is required"):
        await provider.synthesize(text="Hello", voice="", language="ig")


@pytest.mark.asyncio
async def test_naijalingo_synthesize_success():
    provider = NaijaLingoProvider(api_key="test_key")

    mock_client = MagicMock()
    mock_audio_response = MagicMock()
    mock_audio_response.content = b"fake-wav-audio"
    mock_audio_response.media_type = "audio/wav"
    mock_client.tts.generate.return_value = mock_audio_response

    with patch.object(provider, "_get_client", return_value=mock_client):
        result = await provider.synthesize(
            text="Emechaala nnyefe gị nke ọma.",
            voice="obianuju_ig",
            language="ig",
        )

        mock_client.tts.generate.assert_called_once_with(
            text="Emechaala nnyefe gị nke ọma.",
            voice="obianuju_ig",
            lang="ig",
            response_format="wav",
        )

        assert isinstance(result, TTSResult)
        assert result.audio == b"fake-wav-audio"
        assert result.content_type == "audio/wav"
        assert result.provider_metadata["provider"] == "naijalingo"
        assert result.provider_metadata["voice"] == "obianuju_ig"
        assert result.provider_metadata["language"] == "ig"


@pytest.mark.asyncio
async def test_naijalingo_sdk_error_wrapping():
    provider = NaijaLingoProvider(api_key="test_key")

    mock_client = MagicMock()
    mock_client.tts.generate.side_effect = Exception("API rate limit exceeded")

    with (
        patch.object(provider, "_get_client", return_value=mock_client),
        pytest.raises(TTSProviderError, match="9jaLingo TTS synthesis failed"),
    ):
        await provider.synthesize(
            text="Hello world",
            voice="maryam_ha",
            language="ha",
        )


@pytest.mark.asyncio
async def test_naijalingo_streaming_success():
    provider = NaijaLingoProvider(api_key="test_key")

    mock_client = MagicMock()
    mock_client.tts.stream.return_value = iter([b"chunk1", b"chunk2"])

    with patch.object(provider, "_get_client", return_value=mock_client):
        chunks = []
        async for chunk in provider.stream(
            text="Hello streaming",
            voice="dora_pcm",
            language="pcm",
        ):
            chunks.append(chunk)

        assert chunks == [b"chunk1", b"chunk2"]
