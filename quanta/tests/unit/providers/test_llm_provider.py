import inspect

import pytest
from pydantic import ValidationError

from app.providers.llm import (
    LLMMessage,
    LLMMessageRole,
    LLMProvider,
    LLMProviderError,
    LLMResponse,
    LLMToolCall,
)


class MockLLMProvider(LLMProvider):
    async def generate(
        self,
        *,
        messages: list[LLMMessage],
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        return LLMResponse(
            content="Mock response",
        )


def test_llm_message_role():
    message = LLMMessage(
        role="assistant",
        content="I can help.",
    )

    assert message.role == LLMMessageRole.ASSISTANT


def test_llm_message():
    message = LLMMessage(
        role="user",
        content="Send money to Amaka.",
    )

    assert message.role == "user"
    assert message.content == "Send money to Amaka."


def test_llm_message_rejects_invalid_role():
    with pytest.raises(ValidationError):
        LLMMessage(
            role="invalid-role",
            content="Hello.",
        )


def test_llm_message_rejects_empty_content():
    with pytest.raises(ValidationError):
        LLMMessage(
            role="user",
            content="",
        )


def test_llm_tool_call():
    tool_call = LLMToolCall(
        id="call_123",
        name="prepare_transfer",
        arguments={
            "amount": 5000,
            "currency": "NGN",
        },
    )

    assert tool_call.id == "call_123"
    assert tool_call.name == "prepare_transfer"
    assert tool_call.arguments["amount"] == 5000


def test_llm_response_with_text():
    response = LLMResponse(
        content="Transfer prepared.",
        finish_reason="stop",
    )

    assert response.content == "Transfer prepared."
    assert response.tool_calls == []
    assert response.finish_reason == "stop"


def test_llm_response_with_tool_call():
    response = LLMResponse(
        tool_calls=[
            LLMToolCall(
                id="call_123",
                name="prepare_transfer",
                arguments={
                    "amount": 5000,
                },
            )
        ],
        finish_reason="tool_use",
    )

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "prepare_transfer"


@pytest.mark.asyncio
async def test_llm_provider_contract():
    provider = MockLLMProvider()

    response = await provider.generate(
        messages=[
            LLMMessage(
                role="user",
                content="Hello.",
            )
        ],
    )

    assert isinstance(response, LLMResponse)
    assert response.content == "Mock response"


def test_llm_provider_error_is_provider_error():
    error = LLMProviderError("Provider failed.")

    assert isinstance(error, Exception)


def test_llm_provider_is_abstract():
    assert inspect.isabstract(LLMProvider)
