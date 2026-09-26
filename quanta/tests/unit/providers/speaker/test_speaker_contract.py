from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.providers.speaker import (
    EnrollmentResult,
    SpeakerConfigurationError,
    SpeakerEnrollmentError,
    SpeakerError,
    SpeakerInputError,
    SpeakerProviderError,
    SpeakerVerificationError,
    VerificationResult,
)
from app.providers.base import ProviderError


def test_enrollment_result_incomplete_has_no_profile():
    result = EnrollmentResult(complete=False, percent_complete=42.5, profile=None)

    assert result.complete is False
    assert result.percent_complete == 42.5
    assert result.profile is None


def test_enrollment_result_complete_carries_profile():
    result = EnrollmentResult(
        complete=True,
        percent_complete=100.0,
        profile=b"opaque-profile-bytes",
        provider="eagle",
    )

    assert result.complete is True
    assert result.profile == b"opaque-profile-bytes"
    assert result.provider == "eagle"


def test_enrollment_result_validates_percent_range():
    with pytest.raises(ValidationError):
        EnrollmentResult(complete=False, percent_complete=101.0)

    with pytest.raises(ValidationError):
        EnrollmentResult(complete=False, percent_complete=-1.0)


def test_verification_result_fields():
    result = VerificationResult(
        verified=True,
        score=0.93,
        threshold=0.8,
        provider="eagle",
        metadata={"filename": "clip.wav"},
    )

    assert result.verified is True
    assert result.score == 0.93
    assert result.threshold == 0.8
    assert result.metadata == {"filename": "clip.wav"}


def test_verification_result_validates_score_and_threshold_range():
    with pytest.raises(ValidationError):
        VerificationResult(verified=True, score=1.5, threshold=0.8)

    with pytest.raises(ValidationError):
        VerificationResult(verified=True, score=0.5, threshold=-0.1)


def test_error_hierarchy():
    base_err = SpeakerError("base")
    config_err = SpeakerConfigurationError("config")
    input_err = SpeakerInputError("input")
    provider_err = SpeakerProviderError("provider")
    enroll_err = SpeakerEnrollmentError("enroll")
    verify_err = SpeakerVerificationError("verify")

    assert isinstance(base_err, ProviderError)
    assert isinstance(config_err, SpeakerError)
    assert isinstance(input_err, SpeakerError)
    assert isinstance(provider_err, SpeakerError)
    assert isinstance(enroll_err, SpeakerProviderError)
    assert isinstance(verify_err, SpeakerProviderError)
