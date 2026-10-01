"""
Voice Enrollment Service managing speaker voice profile creation via EagleProvider.
"""

from __future__ import annotations

import base64
from typing import Any

from pydantic import BaseModel, Field

from app.core.context import RequestContext
from app.providers.speaker.base import (
    EnrollmentResult,
    SpeakerError,
    SpeakerProvider,
)


class VoiceEnrollmentServiceError(Exception):
    """Application-level service exception for speaker enrollment failures."""


class VoiceEnrollmentResponse(BaseModel):
    """
    Response model for voice enrollment operations.
    """

    request_id: str
    user_id: str
    complete: bool
    percent_complete: float
    profile_available: bool
    # Base64-encoded opaque profile bytes, present only when complete=True.
    # The caller (Node proxy) must store this against the user and send it
    # back on every future voice/interact call - Quanta does not persist it.
    profile_base64: str | None = None
    message: str
    speech_text: str
    provider: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceEnrollmentService:
    """
    Service coordinating voice enrollment for authenticated users.
    Enforces user identity security from RequestContext.
    """

    def __init__(self, *, speaker_provider: SpeakerProvider) -> None:
        self._speaker_provider = speaker_provider

    async def enroll_sample(
        self,
        *,
        context: RequestContext,
        audio: bytes,
        filename: str | None = None,
    ) -> VoiceEnrollmentResponse:
        """
        Process one audio sample for speaker enrollment.
        User identity context comes strictly from context.user_id.
        """
        if not audio or len(audio) == 0:
            raise VoiceEnrollmentServiceError("Audio data cannot be empty.")

        user_id = (context.user_id or "").strip()
        if not user_id:
            raise VoiceEnrollmentServiceError("User identity context is required.")

        try:
            res: EnrollmentResult = await self._speaker_provider.enroll(
                audio=audio,
                filename=filename,
            )
        except SpeakerError as exc:
            raise VoiceEnrollmentServiceError(f"Speaker enrollment failed: {exc}") from exc

        if res.complete:
            msg = "Voice profile enrollment complete! Your voice identity is now enrolled."
            speech = "Voice profile enrollment complete."
        else:
            pct = round(res.percent_complete, 1)
            msg = f"Voice sample accepted ({pct}% complete). Additional audio is required to complete enrollment."
            speech = f"Voice sample accepted. Enrollment is {pct} percent complete. Please speak another phrase."

        profile_base64 = (
            base64.b64encode(res.profile).decode("ascii") if res.profile is not None else None
        )

        return VoiceEnrollmentResponse(
            request_id=str(context.request_id),
            user_id=user_id,
            complete=res.complete,
            percent_complete=res.percent_complete,
            profile_available=res.profile is not None,
            profile_base64=profile_base64,
            message=msg,
            speech_text=speech,
            provider=res.provider,
            metadata=res.metadata,
        )
