from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.response import (
    QuantaResponse,
    ResponseStatus,
    SpeechPayload,
    UIType,
)


def test_success_response():
    request_id = uuid4()
    response = QuantaResponse.success(
        request_id=request_id,
        speech_text="Transfer completed successfully.",
        data={"reference": "txn_123"},
    )

    assert response.request_id == request_id
    assert response.status == ResponseStatus.SUCCESS
    assert response.speech is not None
    assert response.speech.text == "Transfer completed successfully."
    assert response.ui.type == UIType.SUCCESS
    assert response.data == {"reference": "txn_123"}
    assert response.error is None


def test_confirmation_required_response():
    request_id = uuid4()
    response = QuantaResponse.confirmation_required(
        request_id=request_id,
        speech_text="Confirm transfer of five thousand naira to Amaka.",
        data={"amount": 5000, "currency": "NGN"},
    )

    assert response.status == ResponseStatus.CONFIRMATION_REQUIRED
    assert response.ui.type == UIType.TRANSFER_CONFIRMATION
    assert response.speech is not None
    assert response.speech.text.startswith("Confirm transfer")
    assert response.error is None


def test_input_required_response():
    request_id = uuid4()
    response = QuantaResponse.input_required(
        request_id=request_id,
        speech_text="Please provide the account number.",
    )

    assert response.status == ResponseStatus.INPUT_REQUIRED
    assert response.ui.type == UIType.ACCOUNT_INPUT
    assert response.error is None


def test_clarification_required_response():
    request_id = uuid4()
    response = QuantaResponse.clarification_required(
        request_id=request_id,
        speech_text="I found multiple matches. Which Amaka did you mean?",
    )

    assert response.status == ResponseStatus.CLARIFICATION_REQUIRED
    assert response.ui.type == UIType.BENEFICIARY_SELECTION


def test_error_response():
    request_id = uuid4()
    response = QuantaResponse.error_response(
        request_id=request_id,
        code="ACCOUNT_NOT_FOUND",
        message="The account could not be validated.",
        speech_text="I could not validate that account.",
    )

    assert response.status == ResponseStatus.ERROR
    assert response.error is not None
    assert response.error.code == "ACCOUNT_NOT_FOUND"
    assert response.error.message == "The account could not be validated."
    assert response.ui.type == UIType.ERROR
    assert response.data is None


def test_rejects_extra_fields():
    request_id = uuid4()
    with pytest.raises(ValidationError):
        QuantaResponse(
            request_id=request_id,
            status=ResponseStatus.SUCCESS,
            unexpected_field="should-fail",  # type: ignore
        )


def test_request_id_is_required():
    with pytest.raises(ValidationError):
        QuantaResponse(status=ResponseStatus.SUCCESS)  # type: ignore


def test_speech_payload_min_length():
    with pytest.raises(ValidationError):
        SpeechPayload(text="")


def test_response_serialization():
    request_id = uuid4()

    response = QuantaResponse.success(
        request_id=request_id,
        speech_text="Done.",
    )

    payload = response.model_dump(mode="json")

    assert payload["request_id"] == str(request_id)
    assert payload["status"] == "success"
    assert payload["speech"]["text"] == "Done."
    assert payload["ui"]["type"] == "success"
