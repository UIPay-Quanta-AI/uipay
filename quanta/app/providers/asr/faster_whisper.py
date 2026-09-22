from __future__ import annotations

import asyncio
from typing import Any

from app.providers.asr.audio import decode_audio
from app.providers.asr.base import (
    ASRConfigurationError,
    ASRModelLoadError,
    ASRProvider,
    ASRResult,
    ASRTranscriptionError,
    normalize_language,
)


def resolve_faster_whisper_device(device_setting: str) -> str:
    """
    Resolve device setting ('auto', 'cpu', 'cuda').

    Raises ASRConfigurationError if 'cuda' is explicitly requested but unavailable.
    """
    cleaned = device_setting.strip().lower()
    if cleaned == "cpu":
        return "cpu"

    import torch

    cuda_available = torch.cuda.is_available()

    if cleaned == "cuda":
        if not cuda_available:
            raise ASRConfigurationError(
                "CUDA device was explicitly requested for faster-whisper, but CUDA is unavailable."
            )
        return "cuda"

    if cleaned == "auto":
        return "cuda" if cuda_available else "cpu"

    raise ASRConfigurationError(
        f"Invalid device setting '{device_setting}'. Expected 'auto', 'cpu', or 'cuda'."
    )


def resolve_compute_type(compute_type_setting: str, device: str) -> str:
    """
    Resolve compute type setting ('auto', 'float16', 'int8', 'float32', etc.).
    """
    cleaned = compute_type_setting.strip().lower()
    if cleaned == "auto":
        return "float16" if device == "cuda" else "float32"
    return cleaned


class FasterWhisperProvider(ASRProvider):
    """
    Alternative ASR provider implementing faster-whisper (CTranslate2).
    """

    def __init__(
        self,
        *,
        model: str = "large-v3",
        device: str = "auto",
        compute_type: str = "auto",
        max_audio_bytes: int | None = 10_000_000,
        max_duration_seconds: float | None = 60.0,
        model_instance: Any | None = None,
    ) -> None:
        self.model_name = model
        self.device_setting = device
        self.compute_type_setting = compute_type
        self.max_audio_bytes = max_audio_bytes
        self.max_duration_seconds = max_duration_seconds

        self._resolved_device: str | None = None
        self._resolved_compute_type: str | None = None
        self._model_instance: Any | None = model_instance
        self._lock = asyncio.Lock()

    @property
    def resolved_device(self) -> str:
        if self._resolved_device is None:
            self._resolved_device = resolve_faster_whisper_device(self.device_setting)
        return self._resolved_device

    @property
    def resolved_compute_type(self) -> str:
        if self._resolved_compute_type is None:
            self._resolved_compute_type = resolve_compute_type(
                self.compute_type_setting, self.resolved_device
            )
        return self._resolved_compute_type

    def _ensure_loaded(self) -> None:
        """
        Lazy-load faster-whisper model instance if not already initialized.
        """
        if self._model_instance is not None:
            return

        device = self.resolved_device
        compute_type = self.resolved_compute_type

        try:
            from faster_whisper import WhisperModel

            self._model_instance = WhisperModel(
                self.model_name,
                device=device,
                compute_type=compute_type,
            )
        except (ASRModelLoadError, ASRConfigurationError):
            raise
        except Exception as exc:
            raise ASRModelLoadError(
                f"Failed to load faster-whisper model '{self.model_name}': {exc}"
            ) from exc

    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str | None = None,
        language: str | None = None,
    ) -> ASRResult:
        """
        Transcribe audio using faster-whisper.
        """
        normalized_lang = normalize_language(language)

        decoded = decode_audio(
            audio,
            max_bytes=self.max_audio_bytes,
            max_duration=self.max_duration_seconds,
        )

        async with self._lock:
            self._ensure_loaded()

        assert self._model_instance is not None
        model_inst = self._model_instance

        try:

            def _transcribe() -> tuple[list[Any], Any]:
                kwargs: dict[str, Any] = {}
                if normalized_lang:
                    kwargs["language"] = normalized_lang
                segments, info = model_inst.transcribe(decoded.samples, **kwargs)
                return list(segments), info

            segments, info = await asyncio.to_thread(_transcribe)

            text_parts = [seg.text.strip() for seg in segments if getattr(seg, "text", "").strip()]
            text = " ".join(text_parts).strip()

            if not text:
                raise ASRTranscriptionError("faster-whisper transcription output was empty.")

            detected_lang = getattr(info, "language", None) if info else None

            return ASRResult(
                text=text,
                language=normalized_lang or detected_lang,
                confidence=None,
                duration_seconds=decoded.duration_seconds,
                provider="faster_whisper",
                metadata={
                    "model": self.model_name,
                    "device": self.resolved_device,
                    "compute_type": self.resolved_compute_type,
                    "filename": filename or "",
                },
            )

        except (ASRTranscriptionError, ASRModelLoadError):
            raise
        except Exception as exc:
            raise ASRTranscriptionError(f"faster-whisper transcription failed: {exc}") from exc
