import asyncio
import json

from app.core.config import Settings
from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
)
from app.providers.llm.claude import ClaudeProvider


async def main() -> None:
    settings = Settings()

    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

    provider = ClaudeProvider(
        settings=settings,
    )

    response = await provider.generate(
        messages=[
            LLMMessage(
                role=LLMMessageRole.USER,
                content="Find my beneficiary named Mum.",
            )
        ],
        system_prompt=(
            "You are Quanta. "
            "When the user asks to find a saved beneficiary, "
            "use the search_beneficiary tool."
        ),
        tools=[
            {
                "name": "search_beneficiary",
                "description": (
                    "Search the authenticated user's saved beneficiaries "
                    "by nickname or recipient name."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                        }
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            }
        ],
    )

    print("CONTENT:")
    print(response.content)

    print("\nTOOL CALLS:")

    for tool_call in response.tool_calls:
        print(
            json.dumps(
                {
                    "id": tool_call.id,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
