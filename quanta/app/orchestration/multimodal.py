from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.context import RequestContext
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.voice_pipeline import VoicePipeline, VoicePipelineOutcome
from app.providers.ocr.base import OCRError, OCRProvider, OCRResult
from app.schemas.response import QuantaResponse


class ModalityType(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    MULTIMODAL = "multimodal"


class MultimodalInput(BaseModel):
    """
    Normalized container for single or combined multimodal inputs.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    text: str | None = None
    audio: bytes | None = None
    voice_profile: bytes | None = None
    image: bytes | None = None
    filename: str | None = None
    verification_threshold: float | None = None


class MultimodalOutcome(str, Enum):
    SUCCESS = "success"
    SPEAKER_VERIFICATION_FAILED = "speaker_verification_failed"
    ASR_FAILED = "asr_failed"
    OCR_FAILED = "ocr_failed"
    ORCHESTRATION_FAILED = "orchestration_failed"
    EMPTY_INPUT = "empty_input"


class MultimodalResult(BaseModel):
    """
    Normalized result of processing one multimodal interaction.
    """

    outcome: MultimodalOutcome
    modalities_used: list[ModalityType] = Field(default_factory=list)
    ocr_result: OCRResult | None = None
    asr_text: str | None = None
    response: QuantaResponse | None = None
    error: str | None = None


class MultimodalProcessor:
    """
    Thin multimodal coordination layer.

    Coordinates:
    - Image text extraction via OCRProvider
    - Speech recognition & speaker verification via VoicePipeline
    - Context building combining text, voice transcript, and OCR output
    - Delegation to Orchestrator with trusted RequestContext
    """

    def __init__(
        self,
        *,
        orchestrator: Orchestrator,
        ocr_provider: OCRProvider | None = None,
        voice_pipeline: VoicePipeline | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._ocr_provider = ocr_provider
        self._voice_pipeline = voice_pipeline

    async def process(
        self,
        *,
        context: RequestContext,
        input_data: MultimodalInput,
        messages: list[Any] | None = None,
        system_prompt: str | None = None,
    ) -> MultimodalResult:
        modalities: list[ModalityType] = []
        parts: list[str] = []
        ocr_res: OCRResult | None = None
        asr_txt: str | None = None

        # --- 1. Image Modality -----------------------------------------------
        if input_data.image is not None and len(input_data.image) > 0:
            if self._ocr_provider is None:
                return MultimodalResult(
                    outcome=MultimodalOutcome.OCR_FAILED,
                    error="OCR provider is not configured.",
                    response=QuantaResponse.error_response(
                        request_id=context.request_id,
                        code="OCR_PROVIDER_UNAVAILABLE",
                        message="OCR provider is not configured.",
                        speech_text="OCR processing is currently unavailable.",
                        response_language=context.locale,
                    ),
                )
            try:
                ocr_res = await self._ocr_provider.extract(
                    image=input_data.image,
                    filename=input_data.filename,
                )
                modalities.append(ModalityType.IMAGE)
                parts.append(f"[Extracted Image Content (Untrusted Data)]:\n{ocr_res.text.strip()}")
            except OCRError as exc:
                return MultimodalResult(
                    outcome=MultimodalOutcome.OCR_FAILED,
                    error=f"OCR provider failure: {exc}",
                    response=QuantaResponse.error_response(
                        request_id=context.request_id,
                        code="OCR_PROVIDER_FAILURE",
                        message=f"OCR extraction failed: {exc}",
                        speech_text="I couldn't read text from the provided image.",
                        response_language=context.locale,
                    ),
                )

        # --- 2. Voice Modality -----------------------------------------------
        if input_data.audio is not None and len(input_data.audio) > 0:
            if self._voice_pipeline is None:
                return MultimodalResult(
                    outcome=MultimodalOutcome.ASR_FAILED,
                    error="Voice pipeline is not configured.",
                    response=QuantaResponse.error_response(
                        request_id=context.request_id,
                        code="ASR_PROVIDER_UNAVAILABLE",
                        message="Voice pipeline is not configured.",
                        speech_text="Voice processing is currently unavailable.",
                        response_language=context.locale,
                    ),
                )
            pipe_res = await self._voice_pipeline.process(
                context=context,
                audio=input_data.audio,
                voice_profile=input_data.voice_profile,
                verification_threshold=input_data.verification_threshold,
                filename=input_data.filename,
                language=context.locale,
            )
            if pipe_res.outcome == VoicePipelineOutcome.VERIFICATION_FAILED:
                return MultimodalResult(
                    outcome=MultimodalOutcome.SPEAKER_VERIFICATION_FAILED,
                    error=pipe_res.error or "Speaker verification failed.",
                    response=QuantaResponse.error_response(
                        request_id=context.request_id,
                        code="SPEAKER_VERIFICATION_FAILED",
                        message=pipe_res.error or "Speaker verification failed.",
                        speech_text="Speaker verification failed. Please authenticate with PIN.",
                        response_language=context.locale,
                    ),
                )
            if pipe_res.outcome == VoicePipelineOutcome.TRANSCRIPTION_FAILED:
                return MultimodalResult(
                    outcome=MultimodalOutcome.ASR_FAILED,
                    error=pipe_res.error or "Speech recognition failed.",
                    response=QuantaResponse.error_response(
                        request_id=context.request_id,
                        code="ASR_PROVIDER_FAILURE",
                        message=pipe_res.error or "ASR failed.",
                        speech_text="I couldn't understand the audio recording.",
                        response_language=context.locale,
                    ),
                )
            if pipe_res.transcript is not None:
                asr_txt = pipe_res.transcript.text
                modalities.append(ModalityType.VOICE)
                parts.append(f"[Voice Transcript]: {asr_txt.strip()}")

        # --- 3. Text Modality ------------------------------------------------
        if input_data.text is not None and input_data.text.strip():
            modalities.append(ModalityType.TEXT)
            parts.append(f"[User Message]: {input_data.text.strip()}")

        if not parts:
            return MultimodalResult(
                outcome=MultimodalOutcome.EMPTY_INPUT,
                error="No valid input provided across any modality.",
                response=QuantaResponse.error_response(
                    request_id=context.request_id,
                    code="EMPTY_INPUT",
                    message="User input cannot be empty.",
                    response_language=context.locale,
                ),
            )

        combined_input = "\n\n".join(parts)

        # --- 4. Orchestration ------------------------------------------------
        response = await self._orchestrator.process(
            context=context,
            user_input=combined_input,
            messages=messages,
            system_prompt=system_prompt,
        )

        return MultimodalResult(
            outcome=MultimodalOutcome.SUCCESS,
            modalities_used=modalities,
            ocr_result=ocr_res,
            asr_text=asr_txt,
            response=response,
        )
