import pytest

from app.core.context import RequestContext
from app.providers.speaker.base import EnrollmentResult, SpeakerProvider
from app.services.voice_enrollment import VoiceEnrollmentService


class MockSpeakerProvider(SpeakerProvider):
    def __init__(self, complete: bool = True):
        self._complete = complete

    async def enroll(self, *, audio: bytes, filename: str | None = None) -> EnrollmentResult:
        if self._complete:
            return EnrollmentResult(
                complete=True,
                percent_complete=100.0,
                profile=b"mock_profile_bytes",
                provider="mock_eagle",
            )
        return EnrollmentResult(
            complete=False,
            percent_complete=50.0,
            profile=None,
            provider="mock_eagle",
        )

    async def verify(
        self,
        *,
        audio: bytes,
        profile: bytes,
        threshold: float | None = None,
        filename: str | None = None,
    ):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_voice_enrollment_service_complete():
    provider = MockSpeakerProvider(complete=True)
    service = VoiceEnrollmentService(speaker_provider=provider)
    ctx = RequestContext.create(
        user_id="usr_test", session_id="sess_test", operation="VOICE_ENROLLMENT"
    )

    res = await service.enroll_sample(context=ctx, audio=b"fake_audio_pcm")
    assert res.complete is True
    assert res.percent_complete == 100.0
    assert res.profile_available is True
    assert "complete" in res.message.lower()


@pytest.mark.asyncio
async def test_voice_enrollment_service_incomplete():
    provider = MockSpeakerProvider(complete=False)
    service = VoiceEnrollmentService(speaker_provider=provider)
    ctx = RequestContext.create(
        user_id="usr_test", session_id="sess_test", operation="VOICE_ENROLLMENT"
    )

    res = await service.enroll_sample(context=ctx, audio=b"fake_audio_pcm")
    assert res.complete is False
    assert res.percent_complete == 50.0
    assert res.profile_available is False
    assert "additional audio" in res.message.lower()
