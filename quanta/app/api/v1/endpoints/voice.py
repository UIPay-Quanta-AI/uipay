"""
Voice API endpoints for speech recognition, speaker verification, and speaker enrollment.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status

from app.core.constants import Operations
from app.core.context import RequestContext
from app.dependencies.services import get_voice_enrollment_service, get_workflow_runner
from app.orchestration.voice_pipeline import VoicePipelineResult
from app.orchestration.workflow_runner import ConversationalWorkflowRunner
from app.services.voice_enrollment import VoiceEnrollmentResponse, VoiceEnrollmentService

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/interact", response_model=VoicePipelineResult)
async def voice_interact(
    audio: UploadFile = File(...),
    voice_profile: UploadFile | None = File(default=None),
    verification_threshold: float | None = Form(default=None),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    x_locale: str | None = Header(default=None, alias="X-Locale"),
    runner: ConversationalWorkflowRunner = Depends(get_workflow_runner),
) -> VoicePipelineResult:
    """
    Process a voice interaction turn through Speaker Verification -> ASR -> Orchestrator.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-ID header.",
        )

    if not x_session_id or not x_session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-Session-ID header.",
        )

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file cannot be empty.",
        )

    vp_bytes = await voice_profile.read() if voice_profile else None

    context = RequestContext.create(
        user_id=x_user_id,
        session_id=x_session_id,
        operation=Operations.VOICE,
        locale=x_locale,
    )

    return await runner.run_voice_turn(
        context=context,
        audio=audio_bytes,
        voice_profile=vp_bytes,
        verification_threshold=verification_threshold,
        filename=audio.filename,
    )


@router.post("/enroll", response_model=VoiceEnrollmentResponse)
async def voice_enroll(
    audio: UploadFile = File(...),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    x_locale: str | None = Header(default=None, alias="X-Locale"),
    enrollment_service: VoiceEnrollmentService = Depends(get_voice_enrollment_service),
) -> VoiceEnrollmentResponse:
    """
    Feed an audio sample to enroll a user's voice identity via EagleProvider.
    User identity is authoritatively derived from the X-User-ID header.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-ID header.",
        )

    if not x_session_id or not x_session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-Session-ID header.",
        )

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file cannot be empty.",
        )

    context = RequestContext.create(
        user_id=x_user_id,
        session_id=x_session_id,
        operation="VOICE_ENROLLMENT",
        locale=x_locale,
    )

    try:
        return await enrollment_service.enroll_sample(
            context=context,
            audio=audio_bytes,
            filename=audio.filename,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
