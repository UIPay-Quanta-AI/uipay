"""
Interact API endpoint for text, image, and multimodal inputs.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.core.constants import Operations
from app.core.context import RequestContext
from app.dependencies.services import get_workflow_runner
from app.orchestration.multimodal import MultimodalInput
from app.orchestration.workflow_runner import ConversationalWorkflowRunner
from app.schemas.response import QuantaResponse

router = APIRouter(prefix="/interact", tags=["interact"])


class InteractRequest(BaseModel):
    text: str | None = None
    verification_threshold: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("", response_model=QuantaResponse)
async def interact_json(
    body: InteractRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    x_locale: str | None = Header(default=None, alias="X-Locale"),
    x_operation: str | None = Header(default=Operations.TEXT, alias="X-Operation"),
    runner: ConversationalWorkflowRunner = Depends(get_workflow_runner),
) -> QuantaResponse:
    """
    Process a text or JSON-based interaction.
    Requires trusted user context headers from Quanta Proxy / gateway.
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

    context = RequestContext.create(
        user_id=x_user_id,
        session_id=x_session_id,
        operation=x_operation or Operations.TEXT,
        locale=x_locale,
        metadata=body.metadata,
    )

    multimodal_input = MultimodalInput(
        text=body.text,
        verification_threshold=body.verification_threshold,
    )

    return await runner.run_interaction(
        context=context,
        input_data=multimodal_input,
    )


@router.post("/multipart", response_model=QuantaResponse)
async def interact_multipart(
    text: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
    voice_profile: UploadFile | None = File(default=None),
    verification_threshold: float | None = Form(default=None),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    x_locale: str | None = Header(default=None, alias="X-Locale"),
    x_operation: str | None = Header(default=Operations.MULTIMODAL, alias="X-Operation"),
    runner: ConversationalWorkflowRunner = Depends(get_workflow_runner),
) -> QuantaResponse:
    """
    Process a multipart interaction containing text, image file, or audio file.
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

    image_bytes = await image.read() if image else None
    audio_bytes = await audio.read() if audio else None
    vp_bytes = await voice_profile.read() if voice_profile else None

    filename = image.filename if image else (audio.filename if audio else None)

    context = RequestContext.create(
        user_id=x_user_id,
        session_id=x_session_id,
        operation=x_operation or Operations.MULTIMODAL,
        locale=x_locale,
    )

    multimodal_input = MultimodalInput(
        text=text,
        image=image_bytes,
        audio=audio_bytes,
        voice_profile=vp_bytes,
        filename=filename,
        verification_threshold=verification_threshold,
    )

    return await runner.run_interaction(
        context=context,
        input_data=multimodal_input,
    )
