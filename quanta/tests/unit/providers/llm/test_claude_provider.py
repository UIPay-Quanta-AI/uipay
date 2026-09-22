from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
)
from app.providers.llm.claude import ClaudeProvider


def make_settings() -> Settings:
    return Settings(
        ANTHROPIC_API_KEY="test-key",
        CLAUDE_MODEL="claude-sonnet-5",
        CLAUDE_MAX_TOKENS=2048,
        CLAUDE_TIMEOUT_SECONDS=60.0,
        CLAUDE_MAX_RETRIES=2,
    )


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeAnthropicClient:
    def __init__(self, response):
        self.messages = FakeMessages(response)


def make_text_response():
    return SimpleNamespace(
        model="claude-sonnet-5",
        stop_reason="end_turn",
        content=[
            SimpleNamespace(
                type="text",
                text="Hello from Claude.",
            )
        ],
        usage=SimpleNamespace(
            input_tokens=12,
            output_tokens=6,
            cache_read_input_tokens=None,
            cache_creation_input_tokens=None,
        ),
        _request_id="req_test",
    )


def make_tool_response():
    return SimpleNamespace(
        model="claude-sonnet-5",
        stop_reason="tool_use",
        content=[
            SimpleNamespace(
                type="tool_use",
                id="toolu_123",
                name="search_beneficiary",
                input={
                    "query": "Mum",
                },
            )
        ],
        usage=SimpleNamespace(
            input_tokens=20,
            output_tokens=10,
            cache_read_input_tokens=None,
            cache_creation_input_tokens=None,
        ),
        _request_id="req_tool",
    )


@pytest.mark.asyncio
async def test_claude_provider_normalizes_text_response():
    client = FakeAnthropicClient(make_text_response())

    provider = ClaudeProvider(
        settings=make_settings(),
        client=client,
    )

    response = await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Hello",
            )
        ],
    )

    assert response.content == "Hello from Claude."
    assert response.tool_calls == []
    assert response.finish_reason == "end_turn"
    assert response.provider_metadata["model"] == "claude-sonnet-5"
    assert response.provider_metadata["request_id"] == "req_test"


@pytest.mark.asyncio
async def test_claude_provider_normalizes_tool_call():
    client = FakeAnthropicClient(make_tool_response())

    provider = ClaudeProvider(
        settings=make_settings(),
        client=client,
    )

    response = await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Find Mum",
            )
        ],
        tools=[
            {
                "name": "search_beneficiary",
                "description": "Search beneficiaries.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                        }
                    },
                    "required": ["query"],
                },
            }
        ],
    )

    assert len(response.tool_calls) == 1

    tool_call = response.tool_calls[0]

    assert tool_call.id == "toolu_123"
    assert tool_call.name == "search_beneficiary"
    assert tool_call.arguments == {"query": "Mum"}


@pytest.mark.asyncio
async def test_claude_provider_builds_system_prompt():
    client = FakeAnthropicClient(make_text_response())

    provider = ClaudeProvider(
        settings=make_settings(),
        client=client,
    )

    await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Hello",
            )
        ],
        system_prompt="You are Quanta.",
    )

    request = client.messages.calls[0]

    assert request["system"] == "You are Quanta."


@pytest.mark.asyncio
async def test_claude_provider_builds_tool_definition():
    client = FakeAnthropicClient(make_text_response())

    provider = ClaudeProvider(
        settings=make_settings(),
        client=client,
    )

    await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Find Mum",
            )
        ],
        tools=[
            {
                "name": "search_beneficiary",
                "description": "Search beneficiaries.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                },
            }
        ],
    )

    request = client.messages.calls[0]

    assert request["tools"][0]["name"] == "search_beneficiary"
    assert request["tools"][0]["input_schema"]["type"] == "object"


@pytest.mark.asyncio
async def test_claude_provider_reconstructs_assistant_tool_use():
    client = FakeAnthropicClient(make_text_response())

    provider = ClaudeProvider(
        settings=make_settings(),
        client=client,
    )

    await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.ASSISTANT,
                content="Thinking...",
            ),
        ],
    )

    request = client.messages.calls[0]

    assert request["messages"][0]["role"] == "assistant"


@pytest.mark.asyncio
async def test_claude_provider_reconstructs_tool_result():
    client = FakeAnthropicClient(make_text_response())

    provider = ClaudeProvider(
        settings=make_settings(),
        client=client,
    )

    await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.TOOL,
                tool_call_id="toolu_123",
                content='{"success":true}',
            )
        ],
    )

    request = client.messages.calls[0]

    assert request["messages"][0]["role"] == "user"
    assert request["messages"][0]["content"][0]["type"] == "tool_result"
    assert request["messages"][0]["content"][0]["tool_use_id"] == "toolu_123"


def test_claude_provider_requires_api_key():
    settings = make_settings()
    settings.ANTHROPIC_API_KEY = None

    with pytest.raises(
        ValueError,
        match="ANTHROPIC_API_KEY is required",
    ):
        ClaudeProvider(settings=settings)
