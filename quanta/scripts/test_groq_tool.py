import asyncio
import json

from groq import AsyncGroq

from app.core.config import Settings


async def main() -> None:
    settings = Settings()
    api_key = settings.GROQ_API_KEY

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")

    client = AsyncGroq(
        api_key=api_key,
        timeout=settings.GROQ_TIMEOUT_SECONDS,
        max_retries=settings.GROQ_MAX_RETRIES,
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_beneficiary",
                "description": (
                    "Search the authenticated user's saved beneficiaries "
                    "by nickname or recipient name."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Recipient nickname or name.",
                        }
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        }
    ]

    response = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are Quanta. "
                    "When the user asks to find a saved beneficiary, "
                    "use the search_beneficiary tool."
                ),
            },
            {
                "role": "user",
                "content": "Send ₦5,000 to Mum.",
            },
        ],
        tools=tools,
        tool_choice="auto",
        max_completion_tokens=500,
    )

    message = response.choices[0].message

    print("CONTENT:")
    print(message.content)

    print("\nTOOL CALLS:")
    for tool_call in message.tool_calls or []:
        print(
            json.dumps(
                {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
