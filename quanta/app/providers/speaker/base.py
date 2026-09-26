from __future__ import annotations

from abc import abstractmethod

from pydantic import BaseModel, Field

from app.providers.base import Provider, ProviderError

# ---------------------------------------------------------------------------
# Error Hierarchy
# ---------------------------------------------------------------------------


class SpeakerError(ProviderError):
    """
    Base exception for all speaker-verification subsystem errors.
    """


class SpeakerConfigurationError(SpeakerError):
    """
    Raised when speaker-verification configuration (access key, provider) is invalid.
    """


class SpeakerInputError(SpeakerError):
    """
    Raised when input audio or a stored voice profile is invalid.
    """


class SpeakerProviderError(SpeakerError):
    """
    Raised when a speaker-verification provider fails during execution.
    """


class SpeakerEnrollmentError(SpeakerProviderError):
    """
    Raised when a speaker enrollment operation fails.
    """


class SpeakerVerificationError(SpeakerProviderError):
    """
    Raised when a speaker verification operation fails.
    """


# Models


class EnrollmentResult(BaseModel):
    """
    Result of one enrollment call.

    complete=False means the supplied audio was accepted but is not yet
    enough to build a usable profile; `profile` stays None until
    complete=True. The underlying engine cannot resume a partially built
    profile from an exported blob, so callers needing multi-turn enrollment
    ("say a few more sentences") must accumulate audio themselves and call
    enroll() again with the combined recording — this provider only ever
    sees one call's worth of audio at a time.
    """

    complete: bool
    percent_complete: float = Field(ge=0.0, le=100.0)
    profile: bytes | None = None
    provider: str = Field(default="unknown")
    metadata: dict[str, str] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    """
    Result of comparing incoming audio against a previously enrolled profile.
    """

    verified: bool
    score: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    provider: str = Field(default="unknown")
    metadata: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract Interface
# ---------------------------------------------------------------------------


class SpeakerProvider(Provider):
    """
    Provider-neutral interface for voice-identity (speaker) verification.

    This answers "is this voice the enrolled owner of this account" — it
    does not transcribe speech (that is the ASR subsystem) and it does not
    authorize a financial operation (that remains UI Pay's PIN boundary). A
    failed, inconclusive, or skipped verification must fall back to PIN;
    it must never be treated as implicit authorization on its own.
    """

    @abstractmethod
    async def enroll(
        self,
        *,
        audio: bytes,
        filename: str | None = None,
    ) -> EnrollmentResult:
        """
        Feed one audio sample toward building a voice profile for a new speaker.
        """
        raise NotImplementedError

    @abstractmethod
    async def verify(
        self,
        *,
        audio: bytes,
        profile: bytes,
        threshold: float | None = None,
        filename: str | None = None,
    ) -> VerificationResult:
        """
        Compare audio against a previously enrolled profile.
        """
        raise NotImplementedError
