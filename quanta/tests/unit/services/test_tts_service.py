from unittest.mock import AsyncMock, patch

import pytest

from app.providers.tts import TTSResult
from app.services.tts import TTSService


@pytest.mark.asyncio
async def test_tts_service_english_female_routing():
    service = TTSService()

    mock_result = TTSResult(
        audio=b"english-audio",
        content_type="audio/mpeg",
        provider_metadata={"provider": "edge", "voice": "en-NG-EzinneNeural"},
    )

    mock_edge = AsyncMock()
    mock_edge.synthesize.return_value = mock_result

    with patch("app.services.tts.get_tts_provider", return_value=mock_edge) as mock_factory:
        result = await service.synthesize(
            text="Your transfer of 5000 NGN was successful.",
            language="en",
            gender="female",
        )

        mock_factory.assert_called_once_with(
            provider_name="edge",
            settings=service.settings,
        )
        mock_edge.synthesize.assert_called_once_with(
            text="Your transfer of 5000 NGN was successful.",
            voice="en-NG-EzinneNeural",
            language="en-NG",
        )

        assert result.audio == b"english-audio"


@pytest.mark.asyncio
async def test_tts_service_igbo_female_routing():
    service = TTSService()

    mock_result = TTSResult(
        audio=b"igbo-audio",
        content_type="audio/wav",
        provider_metadata={"provider": "naijalingo", "voice": "obianuju_ig"},
    )

    mock_naijalingo = AsyncMock()
    mock_naijalingo.synthesize.return_value = mock_result

    with patch("app.services.tts.get_tts_provider", return_value=mock_naijalingo) as mock_factory:
        result = await service.synthesize(
            text="Emechaala nnyefe gị nke ọma.",
            language="ig",
            gender="female",
        )

        mock_factory.assert_called_once_with(
            provider_name="naijalingo",
            settings=service.settings,
        )
        mock_naijalingo.synthesize.assert_called_once_with(
            text="Emechaala nnyefe gị nke ọma.",
            voice="obianuju_ig",
            language="ig",
        )

        assert result.audio == b"igbo-audio"


@pytest.mark.asyncio
async def test_tts_service_override_provider():
    mock_provider = AsyncMock()
    mock_result = TTSResult(
        audio=b"custom-audio",
        content_type="audio/wav",
    )
    mock_provider.synthesize.return_value = mock_result

    service = TTSService(provider=mock_provider)
    result = await service.synthesize(
        text="Test sentence",
        language="yo",
        gender="male",
    )

    mock_provider.synthesize.assert_called_once_with(
        text="Test sentence",
        voice="babatunde_yo",
        language="yo",
    )
    assert result.audio == b"custom-audio"
