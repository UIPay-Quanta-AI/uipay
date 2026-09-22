from __future__ import annotations

import io
import struct
import wave
from unittest.mock import MagicMock

import pytest

from app.providers.asr import ASRResult, FasterWhisperProvider, NaijaVoxProvider


def generate_wav_bytes(duration: float = 0.5) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        frames = [0] * int(duration * 16000)
        wav.writeframes(struct.pack(f"<{len(frames)}h", *frames))
    return buf.getvalue()


@pytest.mark.asyncio
async def test_providers_satisfy_common_asr_result_contract():
    # 1. NaijaVox mock
    mock_nv_proc = MagicMock()
    mock_nv_proc.tokenizer.get_vocab.return_value = {
        "<|pcm|>": 1,
        "<|ig|>": 2,
        "<|yo|>": 3,
        "<|ha|>": 4,
        "<|en|>": 5,
    }
    mock_input = MagicMock()
    mock_input.input_features.to.return_value = "mock_tensor"
    mock_nv_proc.return_value = mock_input
    mock_nv_proc.get_decoder_prompt_ids.return_value = [[1, 10]]
    mock_nv_proc.batch_decode.return_value = ["Oya run Mum 10k for me."]

    mock_nv_mod = MagicMock()
    mock_nv_mod.generate.return_value = "ids"

    naijavox_provider = NaijaVoxProvider(
        device="cpu",
        processor=mock_nv_proc,
        model=mock_nv_mod,
    )

    # 2. faster-whisper mock
    mock_seg = MagicMock()
    mock_seg.text = "Send ten thousand naira to Mum."
    mock_info = MagicMock()
    mock_info.language = "pcm"
    mock_fw_inst = MagicMock()
    mock_fw_inst.transcribe.return_value = ([mock_seg], mock_info)

    faster_whisper_provider = FasterWhisperProvider(
        device="cpu",
        model_instance=mock_fw_inst,
    )

    audio_bytes = generate_wav_bytes(1.0)

    # Transcribe both
    nv_result = await naijavox_provider.transcribe(audio=audio_bytes, language="pcm")
    fw_result = await faster_whisper_provider.transcribe(audio=audio_bytes, language="pcm")

    # Verify both produce valid ASRResult objects obeying the common contract
    for result, expected_provider in [(nv_result, "naijavox"), (fw_result, "faster_whisper")]:
        assert isinstance(result, ASRResult)
        assert isinstance(result.text, str)
        assert len(result.text) > 0
        assert result.language == "pcm"
        assert result.provider == expected_provider
        assert result.duration_seconds is not None
        assert pytest.approx(result.duration_seconds, abs=0.1) == 1.0
        assert isinstance(result.metadata, dict)
