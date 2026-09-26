from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from app.core.context import RequestContext
from app.orchestration.orchestrator import Orchestrator
from app.providers.asr.base import ASRError, ASRProvider, ASRResult
from app.providers.llm.base import LLMMessage
from app.providers.speaker.base import SpeakerError, SpeakerProvider, VerificationResult
from app.schemas.response import QuantaResponse


class VoicePipelineOutcome(str, Enum):
    """
    What stage a voice turn reached. Any value other than SUCCESS means the
    orchestrator (and therefore every tool, including prepare_transfer) was
    never reached for this turn.
    """

    SUCCESS = "success"
    VERIFICATION_UNAVAILABLE = "verification_unavailable"
    VERIFICATION_FAILED = "verification_failed"
    TRANSCRIPTION_FAILED = "transcription_failed"


class VoicePipelineResult(BaseModel):
    """
    Normalized result of one voice turn through the pipeline.

    Callers (the future /v1/voice endpoint) must treat every outcome other
    than SUCCESS as "fall back to PIN", never as a silent pass-through.
    """

    outcome: VoicePipelineOutcome
    verification: VerificationResult | None = None
    transcript: ASRResult | None = None
    response: QuantaResponse | None = None
    error: str | None = None


class VoicePipeline:
    """
    Composes one voice turn: speaker verification, then speech-to-text,
    then orchestration.

        audio in
            -> SpeakerProvider.verify()   (is this the enrolled speaker?)
            -> ASRProvider.transcribe()   (what did they say?)
            -> Orchestrator.process()     (what should Quanta do about it?)

    This class has zero HTTP or transport concerns; it exists so the
    /v1/voice endpoint has a single, already-tested unit to call, and so
    this exact sequence can be exercised end to end without a running
    server.

    Security invariant
    -------------------
    A missing, failed, or inconclusive speaker verification stops the
    pipeline immediately. ASR and the orchestrator are never reached unless
    verification explicitly succeeded — a voice command from an
    unrecognized or unverifiable speaker must never reach the LLM or any
    tool.
    """

    def __init__(
        self,
        *,
        speaker_provider: SpeakerProvider,
        asr_provider: ASRProvider,
        orchestrator: Orchestrator,
    ) -> None:
        self._speaker_provider = speaker_provider
        self._asr_provider = asr_provider
        self._orchestrator = orchestrator

    async def process(
        self,
        *,
        context: RequestContext,
        audio: bytes,
        voice_profile: bytes | None,
        messages: list[LLMMessage] | None = None,
        language: str | None = None,
        verification_threshold: float | None = None,
        filename: str | None = None,
    ) -> VoicePipelineResult:
        """
        Process one voice turn for an already-authenticated user.

        `voice_profile` is the user's previously enrolled Eagle profile
        (opaque bytes, fetched by the caller from wherever it is stored).
        `context.user_id` identifies the account; it is never inferred from
        the audio itself.
        """

        # --- Step 1: speaker verification ------------------------------
        if voice_profile is None:
            return VoicePipelineResult(
                outcome=VoicePipelineOutcome.VERIFICATION_UNAVAILABLE,
                error="No enrolled voice profile is available for this user.",
            )

        try:
            verification = await self._speaker_provider.verify(
                audio=audio,
                profile=voice_profile,
                threshold=verification_threshold,
                filename=filename,
            )
        except SpeakerError as exc:
            return VoicePipelineResult(
                outcome=VoicePipelineOutcome.VERIFICATION_FAILED,
                error=str(exc),
            )

        if not verification.verified:
            return VoicePipelineResult(
                outcome=VoicePipelineOutcome.VERIFICATION_FAILED,
                verification=verification,
            )

        # --- Step 2: speech-to-text --------------------------------------
        try:
            transcript = await self._asr_provider.transcribe(
                audio=audio,
                filename=filename,
                language=language,
            )
        except ASRError as exc:
            return VoicePipelineResult(
                outcome=VoicePipelineOutcome.TRANSCRIPTION_FAILED,
                verification=verification,
                error=str(exc),
            )

        # --- Step 3: orchestration -----------------------------------------
        response = await self._orchestrator.process(
            context=context,
            user_input=transcript.text,
            messages=messages,
        )

        return VoicePipelineResult(
            outcome=VoicePipelineOutcome.SUCCESS,
            verification=verification,
            transcript=transcript,
            response=response,
        )
