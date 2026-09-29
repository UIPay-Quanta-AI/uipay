from __future__ import annotations

import asyncio
from typing import Any

import numpy as np

from app.providers.asr.audio import decode_audio
from app.providers.asr.base import ASRInputError
from app.providers.speaker.base import (
    EnrollmentResult,
    SpeakerConfigurationError,
    SpeakerEnrollmentError,
    SpeakerInputError,
    SpeakerProvider,
    SpeakerVerificationError,
    VerificationResult,
)

DEFAULT_VERIFICATION_THRESHOLD = 0.8


def _to_pcm16(samples: np.ndarray) -> list[int]:
    """
    Convert normalized float32 [-1, 1] samples (as produced by decode_audio)
    to 16-bit linear PCM, which is what Eagle requires.
    """
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16).tolist()


class EagleProvider(SpeakerProvider):
    """
    Speaker-verification provider using Picovoice Eagle.

    Key design decisions
    ---------------------
    Stateless per call
        Each enroll()/verify() call constructs a fresh native EagleProfiler
        or Eagle recognizer, uses it, and always releases it in a finally
        block. Picovoice's native handles are not Python-GC'd and must be
        explicitly `.delete()`d; constructing fresh objects per call also
        avoids sharing native state across concurrent requests, which the
        SDK does not document as thread-safe.

    Async boundary
        Eagle's enrollment and scoring calls are blocking native (ctypes)
        calls. Both are offloaded to a thread via asyncio.to_thread() so the
        FastAPI event loop is not stalled.

    Enrollment is single-call, not a server-side session
        Eagle can only export a profile once enrollment reaches 100%, and a
        partially built profile cannot be resumed from an exported blob.
        This provider therefore treats enrollment as one audio sample in,
        one result out. Collecting several spoken sentences into one longer
        recording (or deciding to prompt for more speech when
        complete=False) is the caller's responsibility, not this provider's.
    """

    def __init__(
        self,
        *,
        access_key: str | None,
        verification_threshold: float = DEFAULT_VERIFICATION_THRESHOLD,
        max_audio_bytes: int | None = 10_000_000,
        max_duration_seconds: float | None = 30.0,
        pveagle_module: Any | None = None,
    ) -> None:
        if not access_key:
            raise SpeakerConfigurationError(
                "PICOVOICE_ACCESS_KEY is not configured. Get a free AccessKey from "
                "console.picovoice.ai and set it in the environment."
            )

        self.access_key = access_key
        self.verification_threshold = verification_threshold
        self.max_audio_bytes = max_audio_bytes
        self.max_duration_seconds = max_duration_seconds

        # Injected for unit testing; None means lazy-import the real SDK.
        self._pveagle: Any | None = pveagle_module

    def _pv(self) -> Any:
        if self._pveagle is None:
            import pveagle

            self._pveagle = pveagle
        return self._pveagle

    def _decode_pcm16(self, audio: bytes) -> list[int]:
        try:
            decoded = decode_audio(
                audio,
                max_bytes=self.max_audio_bytes,
                max_duration=self.max_duration_seconds,
            )
        except ASRInputError as exc:
            raise SpeakerInputError(str(exc)) from exc
        return _to_pcm16(decoded.samples)

    def _run_enroll(self, pcm16: list[int]) -> tuple[float, bytes | None]:
        pveagle = self._pv()
        profiler = pveagle.create_profiler(access_key=self.access_key)
        try:
            frame_length = profiler.frame_length
            percent = 0.0
            i = 0
            while i + frame_length <= len(pcm16) and percent < 100.0:
                percent = profiler.enroll(pcm16[i : i + frame_length])
                i += frame_length

            if percent < 100.0:
                return percent, None

            profile_bytes = profiler.export().to_bytes()
            return percent, profile_bytes
        except pveagle.EagleError as exc:
            raise SpeakerEnrollmentError(f"Eagle enrollment failed: {exc}") from exc
        finally:
            profiler.delete()

    def _run_verify(self, pcm16: list[int], profile_bytes: bytes) -> float:
        pveagle = self._pv()

        try:
            profile = pveagle.EagleProfile.from_bytes(profile_bytes)
        except Exception as exc:
            raise SpeakerInputError(f"Stored voice profile is invalid or corrupted: {exc}") from exc

        recognizer = pveagle.create_recognizer(access_key=self.access_key)
        try:
            chunk = recognizer.min_process_samples
            scores: list[float] = []
            i = 0
            while i + chunk <= len(pcm16):
                result = recognizer.process(pcm16[i : i + chunk], [profile])
                if result is not None:
                    scores.append(result[0])
                i += chunk

            if not scores:
                raise SpeakerVerificationError(
                    "Not enough voiced audio to verify speaker identity. "
                    "Ask the user to speak again, closer to the microphone."
                )

            return max(scores)
        except pveagle.EagleError as exc:
            raise SpeakerVerificationError(f"Eagle verification failed: {exc}") from exc
        finally:
            recognizer.delete()

    async def enroll(
        self,
        *,
        audio: bytes,
        filename: str | None = None,
    ) -> EnrollmentResult:
        """
        Enroll a speaker using Eagle.
        """
        pcm16 = self._decode_pcm16(audio)

        percent, profile_bytes = await asyncio.to_thread(self._run_enroll, pcm16)

        return EnrollmentResult(
            complete=profile_bytes is not None,
            percent_complete=percent,
            profile=profile_bytes,
            provider="eagle",
            metadata={"filename": filename or ""},
        )

    async def verify(
        self,
        *,
        audio: bytes,
        profile: bytes,
        threshold: float | None = None,
        filename: str | None = None,
    ) -> VerificationResult:
        """
        Verify a speaker's identity against a previously enrolled Eagle profile.
        """
        if not profile:
            raise SpeakerInputError("No enrolled voice profile was supplied.")

        pcm16 = self._decode_pcm16(audio)
        effective_threshold = threshold if threshold is not None else self.verification_threshold

        score = await asyncio.to_thread(self._run_verify, pcm16, profile)

        return VerificationResult(
            verified=score >= effective_threshold,
            score=score,
            threshold=effective_threshold,
            provider="eagle",
            metadata={"filename": filename or ""},
        )
