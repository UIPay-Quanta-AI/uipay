import pytest

from app.core.config import Settings
from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
)
from app.providers.llm.groq import GroqProvider


@pytest.mark.asyncio
@pytest.mark.integration
async def test_groq_live_text_completion():
    settings = Settings()

    if not settings.GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY is not configured.")

    provider = GroqProvider(settings=settings)

    response = await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content=(
                    "Reply with a short confirmation that the Quanta LLM integration is working."
                ),
            )
        ],
    )

    assert response.content
    assert response.finish_reason
    assert response.provider_metadata["model"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_groq_live_tool_call():
    settings = Settings()

    if not settings.GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY is not configured.")

    provider = GroqProvider(settings=settings)

    response = await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Find my beneficiary named Mum.",
            )
        ],
        system_prompt=(
            "You are Quanta. "
            "When a user asks to find a saved beneficiary, "
            "use the search_beneficiary tool."
        ),
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "search_beneficiary",
                    "description": ("Search the authenticated user's saved beneficiaries."),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                            }
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                },
            }
        ],
    )

    assert response.tool_calls

    tool_call = response.tool_calls[0]

    assert tool_call.name == "search_beneficiary"
    assert tool_call.arguments["query"]
