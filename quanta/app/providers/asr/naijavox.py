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

NAIJAVOX_TOKEN_MAP: dict[str, str] = {
    "yo": "<|yo|>",
    "ha": "<|ha|>",
    "ig": "<|ig|>",
    "en": "<|en|>",
    "pcm": "<|pcm|>",
}

REQUIRED_SPECIAL_TOKENS: set[str] = {"<|pcm|>", "<|ig|>"}


def resolve_device(device_setting: str) -> str:
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
                "CUDA device was explicitly requested for NaijaVox, but CUDA is unavailable."
            )
        return "cuda"

    if cleaned == "auto":
        return "cuda" if cuda_available else "cpu"

    raise ASRConfigurationError(
        f"Invalid device setting '{device_setting}'. Expected 'auto', 'cpu', or 'cuda'."
    )


class NaijaVoxProvider(ASRProvider):
    """
    Primary ASR provider implementing NaijaVox-2.0 (Axiveri/NaijaVox-2.0).
    """

    def __init__(
        self,
        *,
        model_id: str = "Axiveri/NaijaVox-2.0",
        device: str = "auto",
        max_audio_bytes: int | None = 10_000_000,
        max_duration_seconds: float | None = 60.0,
        processor: Any | None = None,
        model: Any | None = None,
    ) -> None:
        self.model_id = model_id
        self.device_setting = device
        self.max_audio_bytes = max_audio_bytes
        self.max_duration_seconds = max_duration_seconds

        self._resolved_device: str | None = None
        self._processor: Any | None = processor
        self._model: Any | None = model
        self._lock = asyncio.Lock()

    @property
    def resolved_device(self) -> str:
        if self._resolved_device is None:
            self._resolved_device = resolve_device(self.device_setting)
        return self._resolved_device

    def _verify_tokens(self, processor: Any) -> bool:
        """
        Verify that custom tokens (<|pcm|>, <|ig|>) exist in tokenizer.
        """
        try:
            tokenizer = getattr(processor, "tokenizer", processor)
            vocab = tokenizer.get_vocab()
            for token in REQUIRED_SPECIAL_TOKENS:
                if token not in vocab:
                    return False
            return True
        except Exception:  # noqa: BLE001
            return False

    def _load_processor_with_fallback(self) -> Any:
        """
        Load WhisperProcessor with fallback path if standard loading misses custom tokens.
        """
        from transformers import WhisperProcessor

        # Attempt 1: Standard loading
        try:
            processor = WhisperProcessor.from_pretrained(self.model_id)
            if self._verify_tokens(processor):
                return processor
        except Exception:  # noqa: BLE001, S110
            pass

        # Attempt 2: Reconstruction fallback using tokenizer.json
        try:
            from huggingface_hub import hf_hub_download
            from transformers import AutoFeatureExtractor, PreTrainedTokenizerFast

            feature_extractor = AutoFeatureExtractor.from_pretrained(self.model_id)
            tokenizer_json = hf_hub_download(repo_id=self.model_id, filename="tokenizer.json")
            tokenizer = PreTrainedTokenizerFast(tokenizer_file=tokenizer_json)

            # Ensure special tokens added
            existing_vocab = tokenizer.get_vocab()
            missing = [t for t in REQUIRED_SPECIAL_TOKENS if t not in existing_vocab]
            if missing:
                tokenizer.add_special_tokens({"additional_special_tokens": missing})

            processor = WhisperProcessor(feature_extractor=feature_extractor, tokenizer=tokenizer)
            if self._verify_tokens(processor):
                return processor
        except Exception as exc:
            raise ASRModelLoadError(
                f"Failed to load NaijaVox processor via fallback path: {exc}"
            ) from exc

        raise ASRModelLoadError(
            f"NaijaVox processor from {self.model_id} is missing required "
            f"custom tokens ({', '.join(sorted(REQUIRED_SPECIAL_TOKENS))})."
        )

    def _ensure_loaded(self) -> None:
        """
        Lazy-load processor and model if not already initialized.
        """
        if self._processor is not None and self._model is not None:
            return

        device = self.resolved_device
        try:
            import torch
            from transformers import WhisperForConditionalGeneration

            torch_dtype = torch.float16 if device == "cuda" else torch.float32

            if self._processor is None:
                self._processor = self._load_processor_with_fallback()

            if self._model is None:
                model = WhisperForConditionalGeneration.from_pretrained(
                    self.model_id, torch_dtype=torch_dtype
                )
                self._model = model.to(device)

        except (ASRModelLoadError, ASRConfigurationError):
            raise
        except Exception as exc:
            raise ASRModelLoadError(
                f"Failed to load NaijaVox model '{self.model_id}': {exc}"
            ) from exc

    async def transcribe(
        self,
        *,
        audio: bytes,
        filename: str | None = None,
        language: str | None = None,
    ) -> ASRResult:
        """
        Transcribe audio using NaijaVox-2.0.
        """
        normalized_lang = normalize_language(language)

        decoded = decode_audio(
            audio,
            max_bytes=self.max_audio_bytes,
            max_duration=self.max_duration_seconds,
        )

        async with self._lock:
            self._ensure_loaded()

        assert self._processor is not None
        assert self._model is not None
        processor = self._processor
        model = self._model
        device = self.resolved_device

        try:
            import torch

            torch_dtype = torch.float16 if device == "cuda" else torch.float32

            inputs = processor(
                decoded.samples,
                sampling_rate=16000,
                return_tensors="pt",
            )
            input_features = inputs.input_features.to(device, dtype=torch_dtype)

            forced_decoder_ids = None
            if normalized_lang and normalized_lang in NAIJAVOX_TOKEN_MAP:
                lang_token = NAIJAVOX_TOKEN_MAP[normalized_lang]
                try:
                    forced_decoder_ids = processor.get_decoder_prompt_ids(
                        language=lang_token, task="transcribe"
                    )
                except Exception:  # noqa: BLE001
                    forced_decoder_ids = None

            def _generate() -> str:
                gen_kwargs: dict[str, Any] = {
                    "max_new_tokens": 440,
                }
                if forced_decoder_ids is not None:
                    gen_kwargs["forced_decoder_ids"] = forced_decoder_ids

                with torch.no_grad():
                    predicted_ids = model.generate(input_features, **gen_kwargs)

                transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
                return str(transcription).strip()

            text = await asyncio.to_thread(_generate)

            if not text:
                raise ASRTranscriptionError("NaijaVox transcription output was empty.")

            return ASRResult(
                text=text,
                language=normalized_lang,
                confidence=None,
                duration_seconds=decoded.duration_seconds,
                provider="naijavox",
                metadata={
                    "model_id": self.model_id,
                    "device": device,
                    "filename": filename or "",
                },
            )

        except (ASRTranscriptionError, ASRModelLoadError):
            raise
        except Exception as exc:
            raise ASRTranscriptionError(f"NaijaVox transcription failed: {exc}") from exc
