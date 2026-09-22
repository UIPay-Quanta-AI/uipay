from __future__ import annotations

import io
import struct
import wave
from unittest.mock import MagicMock, patch

import pytest

from app.providers.asr import (
    ASRConfigurationError,
    ASRResult,
    ASRTranscriptionError,
)
from app.providers.asr.faster_whisper import (
    FasterWhisperProvider,
    resolve_compute_type,
    resolve_faster_whisper_device,
)


def generate_wav_bytes(duration: float = 0.5) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        frames = [0] * int(duration * 16000)
        wav.writeframes(struct.pack(f"<{len(frames)}h", *frames))
    return buf.getvalue()


def test_resolve_faster_whisper_device_cpu():
    assert resolve_faster_whisper_device("cpu") == "cpu"


def test_resolve_faster_whisper_device_cuda_unavailable_raises_error():
    with (
        patch("torch.cuda.is_available", return_value=False),
        pytest.raises(ASRConfigurationError, match="CUDA device was explicitly requested"),
    ):
        resolve_faster_whisper_device("cuda")


def test_resolve_compute_type_auto():
    assert resolve_compute_type("auto", "cpu") == "float32"
    assert resolve_compute_type("auto", "cuda") == "float16"
    assert resolve_compute_type("int8", "cpu") == "int8"


@pytest.mark.asyncio
async def test_faster_whisper_transcribe_success():
    mock_seg1 = MagicMock()
    mock_seg1.text = "Transfer ten thousand naira "
    mock_seg2 = MagicMock()
    mock_seg2.text = "to Mum."

    mock_info = MagicMock()
    mock_info.language = "en"

    mock_model_inst = MagicMock()
    mock_model_inst.transcribe.return_value = ([mock_seg1, mock_seg2], mock_info)

    provider = FasterWhisperProvider(
        device="cpu",
        model_instance=mock_model_inst,
    )

    audio = generate_wav_bytes(0.5)
    result = await provider.transcribe(audio=audio, language="en")

    assert isinstance(result, ASRResult)
    assert result.text == "Transfer ten thousand naira to Mum."
    assert result.language == "en"
    assert result.provider == "faster_whisper"
    assert result.metadata["device"] == "cpu"


@pytest.mark.asyncio
async def test_faster_whisper_empty_output_raises_transcription_error():
    mock_info = MagicMock()
    mock_model_inst = MagicMock()
    mock_model_inst.transcribe.return_value = ([], mock_info)

    provider = FasterWhisperProvider(
        device="cpu",
        model_instance=mock_model_inst,
    )

    audio = generate_wav_bytes(0.5)
    with pytest.raises(ASRTranscriptionError, match="empty"):
        await provider.transcribe(audio=audio)
