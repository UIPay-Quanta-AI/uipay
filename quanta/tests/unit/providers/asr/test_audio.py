from __future__ import annotations

import io
import math
import struct
import wave

import numpy as np
import pytest

from app.providers.asr import ASRInputError
from app.providers.asr.audio import DecodedAudio, decode_audio


def generate_synthetic_wav(
    duration_seconds: float = 1.0,
    sample_rate: int = 16000,
    channels: int = 1,
) -> bytes:
    """Generate in-memory WAV audio bytes for testing."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        num_frames = int(duration_seconds * sample_rate)
        raw_samples = [
            int(32767 * 0.5 * math.sin(2 * math.pi * 440 * i / sample_rate))
            for i in range(num_frames * channels)
        ]
        wav.writeframes(struct.pack(f"<{len(raw_samples)}h", *raw_samples))
    return buf.getvalue()


def test_decode_audio_valid_wav_mono():
    wav_bytes = generate_synthetic_wav(duration_seconds=1.5, sample_rate=16000, channels=1)
    decoded = decode_audio(wav_bytes)

    assert isinstance(decoded, DecodedAudio)
    assert decoded.sample_rate == 16000
    assert decoded.channels == 1
    assert isinstance(decoded.samples, np.ndarray)
    assert decoded.samples.dtype == np.float32
    assert pytest.approx(decoded.duration_seconds, abs=0.1) == 1.5


def test_decode_audio_valid_wav_stereo_converts_to_mono():
    wav_bytes = generate_synthetic_wav(duration_seconds=1.0, sample_rate=44100, channels=2)
    decoded = decode_audio(wav_bytes)

    assert isinstance(decoded, DecodedAudio)
    assert decoded.sample_rate == 16000
    assert decoded.channels == 1
    assert pytest.approx(decoded.duration_seconds, abs=0.1) == 1.0


def test_decode_audio_empty_bytes_raises_error():
    with pytest.raises(ASRInputError, match="Audio input is empty"):
        decode_audio(b"")


def test_decode_audio_exceeds_max_bytes():
    wav_bytes = generate_synthetic_wav(duration_seconds=1.0)
    with pytest.raises(ASRInputError, match="payload size"):
        decode_audio(wav_bytes, max_bytes=50)


def test_decode_audio_exceeds_max_duration():
    wav_bytes = generate_synthetic_wav(duration_seconds=3.0)
    with pytest.raises(ASRInputError, match="duration"):
        decode_audio(wav_bytes, max_duration=1.5)


def test_decode_audio_corrupt_data_raises_error():
    with pytest.raises(ASRInputError, match="Failed to open audio stream"):
        decode_audio(b"this is not a valid audio file")
