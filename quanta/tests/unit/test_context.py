from uuid import UUID

import pytest

from app.core.constants import Operations
from app.core.context import RequestContext


def test_context_creation():
    context = RequestContext.create(
        user_id="user_123",
        session_id="session_456",
        operation=Operations.VOICE,
    )

    assert context.user_id == "user_123"
    assert context.session_id == "session_456"
    assert context.operation == Operations.VOICE
    assert context.locale == "en-NG"
    assert isinstance(context.request_id, UUID)


def test_request_ids_are_unique():
    context_one = RequestContext.create(
        user_id="user_123",
        session_id="session_456",
        operation=Operations.VOICE,
    )

    context_two = RequestContext.create(
        user_id="user_123",
        session_id="session_456",
        operation=Operations.VOICE,
    )

    assert context_one.request_id != context_two.request_id


def test_metadata_is_preserved():
    context = RequestContext.create(
        user_id="user_123",
        session_id="session_456",
        operation=Operations.VOICE,
        metadata={
            "channel": "voice",
            "client": "ui-pay",
        },
    )

    assert context.metadata["channel"] == "voice"
    assert context.metadata["client"] == "ui-pay"


def test_empty_user_id_is_rejected():
    with pytest.raises(ValueError, match="user_id cannot be empty"):
        RequestContext.create(
            user_id="",
            session_id="session_456",
            operation=Operations.VOICE,
        )


def test_empty_session_id_is_rejected():
    with pytest.raises(ValueError, match="session_id cannot be empty"):
        RequestContext.create(
            user_id="user_123",
            session_id="",
            operation=Operations.VOICE,
        )


def test_empty_operation_is_rejected():
    with pytest.raises(ValueError, match="operation cannot be empty"):
        RequestContext.create(
            user_id="user_123",
            session_id="session_456",
            operation="",
        )


def test_context_is_immutable():
    context = RequestContext.create(
        user_id="user_123",
        session_id="session_456",
        operation=Operations.VOICE,
    )

    with pytest.raises(AttributeError):
        context.user_id = "attacker"

def test_log_dict_excludes_metadata():
    context = RequestContext.create(
        user_id="user_123",
        session_id="session_456",
        operation=Operations.VOICE,
        metadata={
            "channel": "voice",
            "internal_value": "should-not-be-logged",
        },
    )

    log_data = context.to_log_dict()

    assert "channel" not in log_data
    assert "internal_value" not in log_data
    assert "request_id" in log_data
    assert "user_id" in log_data