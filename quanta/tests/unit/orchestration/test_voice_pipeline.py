from __future__ import annotations

import pytest

from app.core.context import RequestContext
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.voice_pipeline import VoicePipeline, VoicePipelineOutcome
from app.providers.asr.base import ASRResult, ASRTranscriptionError
from app.providers.llm.base import LLMMessageRole, LLMResponse
from app.providers.speaker.base import SpeakerVerificationError, VerificationResult
from app.schemas.response import ResponseStatus
from app.tools.executor import ToolExecutor
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry


def make_context() -> RequestContext:
    return RequestContext.create(
        user_id="user-123",
        session_id="session-123",
        operation="voice",
    )


class FakeSpeakerProvider:
    """Test double: no real Eagle SDK involved, full control over the result."""

    def __init__(
        self, *, result: VerificationResult | None = None, error: Exception | None = None
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict] = []

    async def verify(self, *, audio, profile, threshold=None, filename=None):
        self.calls.append(
            {"audio": audio, "profile": profile, "threshold": threshold, "filename": filename}
        )
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result

    async def enroll(self, *, audio, filename=None):  # pragma: no cover - unused by the pipeline
        raise NotImplementedError


class FakeASRProvider:
    """Test double: no real NaijaVox/faster-whisper model involved."""

    def __init__(self, *, result: ASRResult | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict] = []

    async def transcribe(self, *, audio, filename=None, language=None):
        self.calls.append({"audio": audio, "filename": filename, "language": language})
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


class PoisonOrchestrator:
    """An orchestrator stand-in that fails the test if it is ever called."""

    async def process(self, *, context, user_input, messages=None, initial_state=None):
        raise AssertionError(
            "Orchestrator.process() must not be called when verification "
            "did not succeed or transcription failed."
        )


class MockLLMProvider:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def generate(self, *, messages, system_prompt=None, tools=None):
        self.calls.append({"messages": messages, "system_prompt": system_prompt, "tools": tools})
        return self.responses.pop(0)


def make_real_orchestrator(*, llm_response_text: str) -> tuple[Orchestrator, MockLLMProvider]:
    llm_provider = MockLLMProvider(responses=[LLMResponse(content=llm_response_text)])
    registry = ToolRegistry()
    executor = ToolExecutor(registry=registry, policy=ToolPolicy())
    orchestrator = Orchestrator(
        llm_provider=llm_provider,
        tool_registry=registry,
        tool_executor=executor,
    )
    return orchestrator, llm_provider


@pytest.mark.asyncio
async def test_missing_profile_skips_asr_and_orchestrator():
    speaker = FakeSpeakerProvider()
    asr = FakeASRProvider()
    pipeline = VoicePipeline(
        speaker_provider=speaker,
        asr_provider=asr,
        orchestrator=PoisonOrchestrator(),
    )

    result = await pipeline.process(
        context=make_context(),
        audio=b"raw-audio-bytes",
        voice_profile=None,
    )

    assert result.outcome == VoicePipelineOutcome.VERIFICATION_UNAVAILABLE
    assert result.verification is None
    assert result.transcript is None
    assert result.response is None
    assert speaker.calls == []
    assert asr.calls == []


@pytest.mark.asyncio
async def test_speaker_error_returns_verification_failed_and_skips_asr():
    speaker = FakeSpeakerProvider(error=SpeakerVerificationError("not enough voiced audio"))
    asr = FakeASRProvider()
    pipeline = VoicePipeline(
        speaker_provider=speaker,
        asr_provider=asr,
        orchestrator=PoisonOrchestrator(),
    )

    result = await pipeline.process(
        context=make_context(),
        audio=b"raw-audio-bytes",
        voice_profile=b"stored-profile",
    )

    assert result.outcome == VoicePipelineOutcome.VERIFICATION_FAILED
    assert result.error == "not enough voiced audio"
    assert asr.calls == []


@pytest.mark.asyncio
async def test_verification_below_threshold_returns_verification_failed_and_skips_asr():
    speaker = FakeSpeakerProvider(
        result=VerificationResult(verified=False, score=0.2, threshold=0.8, provider="eagle")
    )
    asr = FakeASRProvider()
    pipeline = VoicePipeline(
        speaker_provider=speaker,
        asr_provider=asr,
        orchestrator=PoisonOrchestrator(),
    )

    result = await pipeline.process(
        context=make_context(),
        audio=b"raw-audio-bytes",
        voice_profile=b"stored-profile",
    )

    assert result.outcome == VoicePipelineOutcome.VERIFICATION_FAILED
    assert result.verification is not None
    assert result.verification.verified is False
    assert asr.calls == []


@pytest.mark.asyncio
async def test_asr_error_returns_transcription_failed_and_skips_orchestrator():
    speaker = FakeSpeakerProvider(
        result=VerificationResult(verified=True, score=0.95, threshold=0.8, provider="eagle")
    )
    asr = FakeASRProvider(error=ASRTranscriptionError("transcription output was empty"))
    pipeline = VoicePipeline(
        speaker_provider=speaker,
        asr_provider=asr,
        orchestrator=PoisonOrchestrator(),
    )

    result = await pipeline.process(
        context=make_context(),
        audio=b"raw-audio-bytes",
        voice_profile=b"stored-profile",
    )

    assert result.outcome == VoicePipelineOutcome.TRANSCRIPTION_FAILED
    assert result.verification is not None
    assert result.verification.verified is True
    assert result.error == "transcription output was empty"


@pytest.mark.asyncio
async def test_full_success_path_passes_transcript_into_real_orchestrator():
    speaker = FakeSpeakerProvider(
        result=VerificationResult(verified=True, score=0.99, threshold=0.8, provider="eagle")
    )
    asr = FakeASRProvider(
        result=ASRResult(text="send 5k to mum", language="pcm", provider="naijavox")
    )
    orchestrator, llm_provider = make_real_orchestrator(llm_response_text="Sure, one moment.")

    pipeline = VoicePipeline(
        speaker_provider=speaker,
        asr_provider=asr,
        orchestrator=orchestrator,
    )

    result = await pipeline.process(
        context=make_context(),
        audio=b"raw-audio-bytes",
        voice_profile=b"stored-profile",
        language="pcm",
        filename="turn.wav",
    )

    assert result.outcome == VoicePipelineOutcome.SUCCESS
    assert result.verification is not None and result.verification.verified is True
    assert result.transcript is not None and result.transcript.text == "send 5k to mum"
    assert result.response is not None
    assert result.response.status == ResponseStatus.SUCCESS
    assert result.response.speech is not None
    assert result.response.speech.text == "Sure, one moment."

    # The orchestrator must have actually received the ASR transcript as the
    # user's turn, not the raw audio or something else.
    assert len(llm_provider.calls) == 1
    sent_messages = llm_provider.calls[0]["messages"]
    assert sent_messages[-1].role == LLMMessageRole.USER
    assert sent_messages[-1].content == "send 5k to mum"

    # Both verify() and transcribe() must have seen the same recorded audio.
    assert speaker.calls[0]["audio"] == b"raw-audio-bytes"
    assert asr.calls[0]["audio"] == b"raw-audio-bytes"
    assert asr.calls[0]["language"] == "pcm"
    assert asr.calls[0]["filename"] == "turn.wav"
