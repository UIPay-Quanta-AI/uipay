import asyncio

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

    response = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are testing Quanta's LLM connection. Respond with exactly: GROQ_OK"
                ),
            },
            {
                "role": "user",
                "content": "Test the connection.",
            },
        ],
        max_completion_tokens=512,
    )

    print(response.choices[0].message.content)


if __name__ == "__main__":
    asyncio.run(main())
