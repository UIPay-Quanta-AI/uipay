from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import av
import numpy as np

from app.providers.asr.base import ASRInputError


@dataclass
class DecodedAudio:
    """
    Normalized internal audio representation (mono, 16 kHz float32).
    """

    samples: np.ndarray
    sample_rate: int = 16000
    duration_seconds: float = 0.0
    channels: int = 1


def decode_audio(
    audio: bytes,
    *,
    max_bytes: int | None = None,
    max_duration: float | None = None,
) -> DecodedAudio:
    """
    Decode raw audio bytes into normalized 16 kHz mono float32 PCM samples.

    Raises ASRInputError if input is empty, oversized, corrupt, or unreadable.
    """
    if not audio:
        raise ASRInputError("Audio input is empty.")

    if max_bytes is not None and len(audio) > max_bytes:
        raise ASRInputError(
            f"Audio payload size ({len(audio)} bytes) exceeds maximum limit ({max_bytes} bytes)."
        )

    try:
        container: Any = av.open(io.BytesIO(audio))
    except Exception as exc:
        raise ASRInputError(f"Failed to open audio stream with PyAV: {exc}") from exc

    try:
        audio_streams = container.streams.audio
        if not audio_streams:
            raise ASRInputError("Media file contains no usable audio stream.")

        stream = audio_streams[0]
        resampler = av.AudioResampler(format="flt", layout="mono", rate=16000)

        chunks: list[np.ndarray] = []
        for frame in container.decode(stream):
            resampled = resampler.resample(frame)
            if resampled:
                for r_frame in resampled:
                    chunks.append(r_frame.to_ndarray().flatten())

        flushed = resampler.resample(None)
        if flushed:
            for r_frame in flushed:
                chunks.append(r_frame.to_ndarray().flatten())

    except ASRInputError:
        raise
    except Exception as exc:
        raise ASRInputError(f"Failed to decode audio frames: {exc}") from exc
    finally:
        container.close()

    if not chunks:
        raise ASRInputError("Audio file produced no usable audio samples.")

    samples = np.concatenate(chunks, axis=0).astype(np.float32)
    if samples.size == 0:
        raise ASRInputError("Audio file produced no usable audio samples.")

    duration_seconds = float(samples.size) / 16000.0

    if max_duration is not None and duration_seconds > max_duration:
        raise ASRInputError(
            f"Audio duration ({duration_seconds:.2f}s) exceeds maximum limit ({max_duration:.2f}s)."
        )

    return DecodedAudio(
        samples=samples,
        sample_rate=16000,
        duration_seconds=duration_seconds,
        channels=1,
    )
