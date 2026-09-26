from __future__ import annotations

import io
import itertools
import struct
import wave
from unittest.mock import MagicMock

import pytest

from app.providers.speaker import (
    SpeakerConfigurationError,
    SpeakerEnrollmentError,
    SpeakerInputError,
    SpeakerVerificationError,
)
from app.providers.speaker.eagle import EagleProvider


def generate_wav_bytes(duration: float = 0.5) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        frames = [0] * int(duration * 16000)
        wav.writeframes(struct.pack(f"<{len(frames)}h", *frames))
    return buf.getvalue()


class MockEagleError(Exception):
    """Stand-in for pveagle.EagleError so `except pveagle.EagleError` works."""


def create_mock_pveagle(
    *,
    enroll_percentages: list[float] | None = None,
    exported_profile: bytes = b"exported-profile-bytes",
    frame_length: int = 1600,
    min_process_samples: int = 1600,
    process_scores: list[list[float] | None] | None = None,
    from_bytes_side_effect: Exception | None = None,
) -> MagicMock:
    mock = MagicMock()
    mock.EagleError = MockEagleError

    mock_profiler = MagicMock()
    mock_profiler.frame_length = frame_length
    if enroll_percentages is not None:
        mock_profiler.enroll.side_effect = enroll_percentages
    mock_export = MagicMock()
    mock_export.to_bytes.return_value = exported_profile
    mock_profiler.export.return_value = mock_export
    mock.create_profiler.return_value = mock_profiler

    mock_recognizer = MagicMock()
    mock_recognizer.min_process_samples = min_process_samples
    if process_scores is not None:
        # cycle() so a short list still covers however many chunks the real
        # decoded audio happens to split into.
        mock_recognizer.process.side_effect = itertools.cycle(process_scores)
    mock.create_recognizer.return_value = mock_recognizer

    if from_bytes_side_effect is not None:
        mock.EagleProfile.from_bytes.side_effect = from_bytes_side_effect
    else:
        mock.EagleProfile.from_bytes.return_value = MagicMock()

    return mock


def test_missing_access_key_raises_configuration_error():
    with pytest.raises(SpeakerConfigurationError, match="PICOVOICE_ACCESS_KEY"):
        EagleProvider(access_key=None)

    with pytest.raises(SpeakerConfigurationError):
        EagleProvider(access_key="")


@pytest.mark.asyncio
async def test_enroll_completes_and_returns_profile():
    mock_pveagle = create_mock_pveagle(
        enroll_percentages=[45.0, 100.0],
        exported_profile=b"final-profile",
        frame_length=1600,
    )
    provider = EagleProvider(access_key="test-key", pveagle_module=mock_pveagle)

    result = await provider.enroll(audio=generate_wav_bytes(0.5))

    assert result.complete is True
    assert result.percent_complete == 100.0
    assert result.profile == b"final-profile"
    assert result.provider == "eagle"
    mock_pveagle.create_profiler.return_value.delete.assert_called_once()


@pytest.mark.asyncio
async def test_enroll_incomplete_returns_no_profile():
    mock_pveagle = create_mock_pveagle(
        enroll_percentages=[20.0, 35.0, 40.0, 40.0, 40.0],
        frame_length=1600,
    )
    provider = EagleProvider(access_key="test-key", pveagle_module=mock_pveagle)

    result = await provider.enroll(audio=generate_wav_bytes(0.5))

    assert result.complete is False
    assert result.profile is None
    assert result.percent_complete == 40.0
    mock_pveagle.create_profiler.return_value.export.assert_not_called()
    mock_pveagle.create_profiler.return_value.delete.assert_called_once()


@pytest.mark.asyncio
async def test_enroll_eagle_error_is_wrapped_and_profiler_still_released():
    mock_pveagle = create_mock_pveagle(frame_length=1600)
    mock_pveagle.create_profiler.return_value.enroll.side_effect = MockEagleError("device busy")

    provider = EagleProvider(access_key="test-key", pveagle_module=mock_pveagle)

    with pytest.raises(SpeakerEnrollmentError, match="Eagle enrollment failed"):
        await provider.enroll(audio=generate_wav_bytes(0.5))

    mock_pveagle.create_profiler.return_value.delete.assert_called_once()


@pytest.mark.asyncio
async def test_verify_above_threshold_is_verified():
    mock_pveagle = create_mock_pveagle(
        min_process_samples=1600,
        process_scores=[[0.95], [0.91]],
    )
    provider = EagleProvider(access_key="test-key", pveagle_module=mock_pveagle)

    result = await provider.verify(audio=generate_wav_bytes(0.5), profile=b"stored-profile")

    assert result.verified is True
    assert result.score == 0.95
    assert result.threshold == 0.8
    mock_pveagle.create_recognizer.return_value.delete.assert_called_once()


@pytest.mark.asyncio
async def test_verify_below_threshold_is_not_verified():
    mock_pveagle = create_mock_pveagle(
        min_process_samples=1600,
        process_scores=[[0.2], [0.1]],
    )
    provider = EagleProvider(access_key="test-key", pveagle_module=mock_pveagle)

    result = await provider.verify(audio=generate_wav_bytes(0.5), profile=b"stored-profile")

    assert result.verified is False
    assert result.score == 0.2


@pytest.mark.asyncio
async def test_verify_respects_explicit_threshold_override():
    mock_pveagle = create_mock_pveagle(
        min_process_samples=1600,
        process_scores=[[0.5], [0.4]],
    )
    provider = EagleProvider(access_key="test-key", pveagle_module=mock_pveagle)

    result = await provider.verify(
        audio=generate_wav_bytes(0.5),
        profile=b"stored-profile",
        threshold=0.4,
    )

    assert result.verified is True
    assert result.threshold == 0.4


@pytest.mark.asyncio
async def test_verify_empty_profile_raises_input_error():
    mock_pveagle = create_mock_pveagle()
    provider = EagleProvider(access_key="test-key", pveagle_module=mock_pveagle)

    with pytest.raises(SpeakerInputError, match="No enrolled voice profile"):
        await provider.verify(audio=generate_wav_bytes(0.5), profile=b"")

    mock_pveagle.create_recognizer.assert_not_called()


@pytest.mark.asyncio
async def test_verify_corrupted_profile_raises_input_error():
    mock_pveagle = create_mock_pveagle(from_bytes_side_effect=ValueError("bad blob"))
    provider = EagleProvider(access_key="test-key", pveagle_module=mock_pveagle)

    with pytest.raises(SpeakerInputError, match="invalid or corrupted"):
        await provider.verify(audio=generate_wav_bytes(0.5), profile=b"garbage")


@pytest.mark.asyncio
async def test_verify_no_voiced_frames_raises_verification_error():
    mock_pveagle = create_mock_pveagle(
        min_process_samples=1600,
        process_scores=[None, None],
    )
    provider = EagleProvider(access_key="test-key", pveagle_module=mock_pveagle)

    with pytest.raises(SpeakerVerificationError, match="Not enough voiced audio"):
        await provider.verify(audio=generate_wav_bytes(0.5), profile=b"stored-profile")

    mock_pveagle.create_recognizer.return_value.delete.assert_called_once()
