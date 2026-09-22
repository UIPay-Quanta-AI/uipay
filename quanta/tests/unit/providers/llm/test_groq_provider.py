from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
)
from app.providers.llm.groq import GroqProvider


def make_settings() -> Settings:
    return Settings(
        GROQ_API_KEY="test-key",
        GROQ_MODEL="openai/gpt-oss-120b",
        GROQ_MAX_TOKENS=2048,
        GROQ_TIMEOUT_SECONDS=60.0,
        GROQ_MAX_RETRIES=2,
        GROQ_DISABLE_PARALLEL_TOOL_USE=True,
    )


class FakeChatCompletions:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeAsyncGroq:
    def __init__(self, response):
        self.chat = SimpleNamespace(completions=FakeChatCompletions(response))


def make_text_response():
    return SimpleNamespace(
        id="chatcmpl_test",
        model="openai/gpt-oss-120b",
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(
                    content="Hello from Groq.",
                    tool_calls=None,
                ),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
        ),
    )


def make_tool_response():
    return SimpleNamespace(
        id="chatcmpl_tool",
        model="openai/gpt-oss-120b",
        choices=[
            SimpleNamespace(
                finish_reason="tool_calls",
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[
                        SimpleNamespace(
                            id="call_123",
                            function=SimpleNamespace(
                                name="search_beneficiary",
                                arguments='{"query":"Mum"}',
                            ),
                        )
                    ],
                ),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=20,
            completion_tokens=10,
        ),
    )


@pytest.mark.asyncio
async def test_groq_provider_normalizes_text_response():
    fake_client = FakeAsyncGroq(make_text_response())

    provider = GroqProvider(
        settings=make_settings(),
        client=fake_client,
    )

    response = await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Hello",
            )
        ],
    )

    assert response.content == "Hello from Groq."
    assert response.tool_calls == []
    assert response.finish_reason == "stop"
    assert response.provider_metadata["model"] == "openai/gpt-oss-120b"
    assert response.provider_metadata["usage"]["input_tokens"] == 10
    assert response.provider_metadata["usage"]["output_tokens"] == 5


@pytest.mark.asyncio
async def test_groq_provider_normalizes_tool_call():
    fake_client = FakeAsyncGroq(make_tool_response())

    provider = GroqProvider(
        settings=make_settings(),
        client=fake_client,
    )

    response = await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Send money to Mum.",
            )
        ],
        tools=[
            {
                "name": "search_beneficiary",
            }
        ],
    )

    assert len(response.tool_calls) == 1

    tool_call = response.tool_calls[0]

    assert tool_call.id == "call_123"
    assert tool_call.name == "search_beneficiary"
    assert tool_call.arguments == {"query": "Mum"}


@pytest.mark.asyncio
async def test_groq_provider_sends_system_prompt():
    fake_client = FakeAsyncGroq(make_text_response())

    provider = GroqProvider(
        settings=make_settings(),
        client=fake_client,
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

    request = fake_client.chat.completions.calls[0]

    assert request["messages"][0] == {
        "role": "system",
        "content": "You are Quanta.",
    }


@pytest.mark.asyncio
async def test_groq_provider_sends_tools():
    fake_client = FakeAsyncGroq(make_tool_response())

    provider = GroqProvider(
        settings=make_settings(),
        client=fake_client,
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_beneficiary",
                "description": "Search beneficiaries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                },
            },
        }
    ]

    await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Find Mum.",
            )
        ],
        tools=tools,
    )

    request = fake_client.chat.completions.calls[0]

    assert request["tools"] == tools
    assert request["parallel_tool_calls"] is False


@pytest.mark.asyncio
async def test_groq_provider_reconstructs_assistant_tool_calls():
    fake_client = FakeAsyncGroq(make_text_response())

    provider = GroqProvider(
        settings=make_settings(),
        client=fake_client,
    )

    messages = [
        LLMMessage(
            role=LLMMessageRole.ASSISTANT,
            content=None,
            tool_calls=[
                {
                    "id": "call_123",
                    "name": "search_beneficiary",
                    "arguments": {"query": "Mum"},
                }
            ],
        )
    ]

    await provider.generate(messages=messages)

    request = fake_client.chat.completions.calls[0]

    assistant = request["messages"][0]

    assert assistant["role"] == "assistant"
    assert assistant["tool_calls"][0]["id"] == "call_123"
    assert assistant["tool_calls"][0]["type"] == "function"
    assert assistant["tool_calls"][0]["function"]["name"] == ("search_beneficiary")
    assert assistant["tool_calls"][0]["function"]["arguments"] == ('{"query":"Mum"}')


@pytest.mark.asyncio
async def test_groq_provider_reconstructs_tool_result():
    fake_client = FakeAsyncGroq(make_text_response())

    provider = GroqProvider(
        settings=make_settings(),
        client=fake_client,
    )

    await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.TOOL,
                content='{"success":true}',
                tool_call_id="call_123",
            )
        ]
    )

    request = fake_client.chat.completions.calls[0]

    assert request["messages"][0] == {
        "role": "tool",
        "tool_call_id": "call_123",
        "content": '{"success":true}',
    }


@pytest.mark.asyncio
async def test_groq_provider_rejects_system_messages():
    fake_client = FakeAsyncGroq(make_text_response())

    provider = GroqProvider(
        settings=make_settings(),
        client=fake_client,
    )

    with pytest.raises(
        ValueError,
        match="System messages must be passed",
    ):
        await provider.generate(
            messages=[
                LLMMessage(
                    role=LLMMessageRole.SYSTEM,
                    content="System",
                )
            ]
        )


@pytest.mark.asyncio
async def test_groq_provider_rejects_tool_message_without_id():
    fake_client = FakeAsyncGroq(make_text_response())

    provider = GroqProvider(
        settings=make_settings(),
        client=fake_client,
    )

    with pytest.raises(
        ValueError,
        match="Tool messages require tool_call_id",
    ):
        await provider.generate(
            messages=[
                LLMMessage(
                    role=LLMMessageRole.TOOL,
                    content="result",
                )
            ]
        )


def test_groq_provider_requires_api_key():
    settings = make_settings()
    settings.GROQ_API_KEY = None

    with pytest.raises(
        ValueError,
        match="GROQ_API_KEY is required",
    ):
        GroqProvider(settings=settings)
