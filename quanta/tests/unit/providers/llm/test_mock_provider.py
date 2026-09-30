import pytest

from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
    LLMResponse,
    LLMToolCall,
)
from app.providers.llm.mock import MockLLMProvider


@pytest.mark.asyncio
async def test_mock_provider_returns_responses_in_order():
    first = LLMResponse(content="First")
    second = LLMResponse(content="Second")

    provider = MockLLMProvider(responses=[first, second])

    result_one = await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Hello",
            )
        ]
    )

    result_two = await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Hello again",
            )
        ]
    )

    assert result_one == first
    assert result_two == second


@pytest.mark.asyncio
async def test_mock_provider_records_calls():
    provider = MockLLMProvider(responses=[LLMResponse(content="Done.")])

    messages = [
        LLMMessage(
            role=LLMMessageRole.USER,
            content="Check my balance.",
        )
    ]

    await provider.generate(
        messages=messages,
        system_prompt="You are Quanta.",
        tools=[{"name": "get_balance"}],
    )

    assert len(provider.calls) == 1
    assert provider.calls[0]["messages"] == messages
    assert provider.calls[0]["system_prompt"] == "You are Quanta."
    assert provider.calls[0]["tools"] == [{"name": "get_balance"}]


@pytest.mark.asyncio
async def test_mock_provider_supports_tool_calls():
    response = LLMResponse(
        tool_calls=[
            LLMToolCall(
                id="call_123",
                name="search_beneficiary",
                arguments={"query": "Mum"},
            )
        ]
    )

    provider = MockLLMProvider(responses=[response])

    result = await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Send money to Mum.",
            )
        ]
    )

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_123"
    assert result.tool_calls[0].name == "search_beneficiary"
    assert result.tool_calls[0].arguments == {"query": "Mum"}


@pytest.mark.asyncio
async def test_mock_provider_raises_when_responses_are_exhausted():
    provider = MockLLMProvider(responses=[LLMResponse(content="Only response")])

    await provider.generate(messages=[])

    with pytest.raises(
        RuntimeError,
        match="no responses remaining",
    ):
        await provider.generate(messages=[])


def test_mock_provider_requires_response_source():
    with pytest.raises(
        ValueError,
        match="Either responses, responder, or default_text must be provided",
    ):
        MockLLMProvider()


def test_mock_provider_rejects_both_response_sources():
    with pytest.raises(
        ValueError,
        match="either responses or responder",
    ):
        MockLLMProvider(
            responses=[LLMResponse(content="A")],
            responder=lambda *_: LLMResponse(content="B"),
        )
