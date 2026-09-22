import pytest
from pydantic import ValidationError

from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
    LLMToolCall,
)


def test_user_message_requires_content():
    message = LLMMessage(
        role=LLMMessageRole.USER,
        content="Hello",
    )

    assert message.content == "Hello"


def test_user_message_rejects_empty_content():
    with pytest.raises(ValidationError):
        LLMMessage(
            role=LLMMessageRole.USER,
            content="   ",
        )


def test_user_message_rejects_tool_calls():
    with pytest.raises(ValidationError):
        LLMMessage(
            role=LLMMessageRole.USER,
            content="Hello",
            tool_calls=[
                LLMToolCall(
                    id="call_1",
                    name="test",
                )
            ],
        )


def test_assistant_message_can_contain_only_tool_calls():
    message = LLMMessage(
        role=LLMMessageRole.ASSISTANT,
        tool_calls=[
            LLMToolCall(
                id="call_1",
                name="search_beneficiary",
                arguments={"query": "Mum"},
            )
        ],
    )

    assert message.content is None
    assert len(message.tool_calls) == 1


def test_assistant_message_can_contain_text():
    message = LLMMessage(
        role=LLMMessageRole.ASSISTANT,
        content="Hello.",
    )

    assert message.content == "Hello."


def test_assistant_message_rejects_empty_message():
    with pytest.raises(ValidationError):
        LLMMessage(
            role=LLMMessageRole.ASSISTANT,
        )


def test_tool_message_requires_tool_call_id():
    with pytest.raises(ValidationError):
        LLMMessage(
            role=LLMMessageRole.TOOL,
            content="Tool result",
        )


def test_tool_message_requires_content():
    with pytest.raises(ValidationError):
        LLMMessage(
            role=LLMMessageRole.TOOL,
            tool_call_id="call_1",
        )


def test_tool_message_is_valid():
    message = LLMMessage(
        role=LLMMessageRole.TOOL,
        content='{"success":true}',
        tool_call_id="call_1",
    )

    assert message.tool_call_id == "call_1"


def test_system_message_requires_content():
    with pytest.raises(ValidationError):
        LLMMessage(
            role=LLMMessageRole.SYSTEM,
        )
