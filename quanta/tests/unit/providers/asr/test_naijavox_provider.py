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
from app.providers.asr.naijavox import NaijaVoxProvider, resolve_device


def generate_wav_bytes(duration: float = 0.5) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        frames = [0] * int(duration * 16000)
        wav.writeframes(struct.pack(f"<{len(frames)}h", *frames))
    return buf.getvalue()


def create_mock_processor(tokens: set[str] | None = None, transcript: str = "Send 10k to Mum."):
    if tokens is None:
        tokens = {"<|pcm|>", "<|ig|>", "<|yo|>", "<|ha|>", "<|en|>"}

    mock_proc = MagicMock()
    mock_proc.tokenizer.get_vocab.return_value = {t: i for i, t in enumerate(tokens)}

    mock_input = MagicMock()
    mock_input.input_features.to.return_value = "mock_tensor"
    mock_proc.return_value = mock_input

    mock_proc.get_decoder_prompt_ids.return_value = [[1, 10]]
    mock_proc.batch_decode.return_value = [transcript]
    return mock_proc


def create_mock_model():
    mock_mod = MagicMock()
    mock_mod.generate.return_value = "mock_ids"
    return mock_mod


def test_resolve_device_cpu():
    assert resolve_device("cpu") == "cpu"


def test_resolve_device_cuda_unavailable_raises_error():
    with (
        patch("torch.cuda.is_available", return_value=False),
        pytest.raises(ASRConfigurationError, match="CUDA device was explicitly requested"),
    ):
        resolve_device("cuda")


@pytest.mark.asyncio
async def test_naijavox_transcribe_success():
    mock_proc = create_mock_processor(transcript="Fi 10000 ranṣẹ si Mum.")
    mock_mod = create_mock_model()

    provider = NaijaVoxProvider(
        device="cpu",
        processor=mock_proc,
        model=mock_mod,
    )

    audio = generate_wav_bytes(0.5)
    result = await provider.transcribe(audio=audio, language="yoruba")

    assert isinstance(result, ASRResult)
    assert result.text == "Fi 10000 ranṣẹ si Mum."
    assert result.language == "yo"
    assert result.provider == "naijavox"
    assert result.metadata["device"] == "cpu"


@pytest.mark.asyncio
async def test_naijavox_transcribe_empty_output_raises_transcription_error():
    mock_proc = create_mock_processor(transcript="   ")
    mock_mod = create_mock_model()

    provider = NaijaVoxProvider(
        device="cpu",
        processor=mock_proc,
        model=mock_mod,
    )

    audio = generate_wav_bytes(0.5)
    with pytest.raises(ASRTranscriptionError, match="empty"):
        await provider.transcribe(audio=audio, language="pcm")


def test_naijavox_missing_custom_tokens_raises_model_load_error():
    mock_proc = MagicMock()
    mock_proc.tokenizer.get_vocab.return_value = {"<|en|>": 1}

    provider = NaijaVoxProvider(device="cpu")

    assert provider._verify_tokens(mock_proc) is False
