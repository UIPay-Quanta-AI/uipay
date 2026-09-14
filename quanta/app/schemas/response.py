from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    CLARIFICATION_REQUIRED = "clarification_required"
    INPUT_REQUIRED = "input_required"
    CONFIRMATION_REQUIRED = "confirmation_required"
    PROCESSING = "processing"
    CANCELLED = "cancelled"
    ERROR = "error"


class UIType(str, Enum):
    NONE = "none"
    TRANSFER_CONFIRMATION = "transfer_confirmation"
    ACCOUNT_INPUT = "account_input"
    BENEFICIARY_SELECTION = "beneficiary_selection"
    BUDGET = "budget"
    BUDGET_QUESTION = "budget_question"
    SUCCESS = "success"
    ERROR = "error"


class SpeechPayload(BaseModel):
    text: str = Field(..., min_length=1)


class UIPayload(BaseModel):
    type: UIType = UIType.NONE


class ErrorPayload(BaseModel):
    code: str
    message: str


class QuantaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    status: ResponseStatus
    speech: SpeechPayload | None = None
    ui: UIPayload = Field(default_factory=UIPayload)
    data: dict[str, Any] | None = None
    error: ErrorPayload | None = None

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def success(
        cls,
        *,
        request_id: UUID,
        speech_text: str | None = None,
        ui_type: UIType = UIType.SUCCESS,
        data: dict[str, Any] | None = None,
    ) -> QuantaResponse:
        payload: dict[str, Any] = {
            "request_id": request_id,
            "status": ResponseStatus.SUCCESS,
            "ui": {"type": ui_type},
            "data": data,
            "error": None,
        }
        if speech_text:
            payload["speech"] = {"text": speech_text}
        return cls.model_validate(payload)

    @classmethod
    def confirmation_required(
        cls,
        *,
        request_id: UUID,
        speech_text: str,
        data: dict[str, Any] | None = None,
    ) -> QuantaResponse:
        return cls.model_validate(
            {
                "request_id": request_id,
                "status": ResponseStatus.CONFIRMATION_REQUIRED,
                "speech": {"text": speech_text},
                "ui": {"type": UIType.TRANSFER_CONFIRMATION},
                "data": data,
                "error": None,
            }
        )

    @classmethod
    def input_required(
        cls,
        *,
        request_id: UUID,
        speech_text: str,
        ui_type: UIType = UIType.ACCOUNT_INPUT,
        data: dict[str, Any] | None = None,
    ) -> QuantaResponse:
        return cls.model_validate(
            {
                "request_id": request_id,
                "status": ResponseStatus.INPUT_REQUIRED,
                "speech": {"text": speech_text},
                "ui": {"type": ui_type},
                "data": data,
                "error": None,
            }
        )

    @classmethod
    def clarification_required(
        cls,
        *,
        request_id: UUID,
        speech_text: str,
        ui_type: UIType = UIType.BENEFICIARY_SELECTION,
        data: dict[str, Any] | None = None,
    ) -> QuantaResponse:
        return cls.model_validate(
            {
                "request_id": request_id,
                "status": ResponseStatus.CLARIFICATION_REQUIRED,
                "speech": {"text": speech_text},
                "ui": {"type": ui_type},
                "data": data,
                "error": None,
            }
        )

    @classmethod
    def error_response(
        cls,
        *,
        request_id: UUID,
        code: str,
        message: str,
        speech_text: str | None = None,
    ) -> QuantaResponse:
        payload: dict[str, Any] = {
            "request_id": request_id,
            "status": ResponseStatus.ERROR,
            "ui": {"type": UIType.ERROR},
            "data": None,
            "error": {"code": code, "message": message},
        }
        if speech_text:
            payload["speech"] = {"text": speech_text}
        return cls.model_validate(payload)
