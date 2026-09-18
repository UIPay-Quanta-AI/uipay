import asyncio

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
                content="Reply with exactly: CLAUDE_OK",
            )
        ],
    )

    print("CONTENT:")
    print(response.content)

    print("\nFINISH REASON:")
    print(response.finish_reason)

    print("\nMODEL:")
    print(response.provider_metadata.get("model"))

    print("\nREQUEST ID:")
    print(response.provider_metadata.get("request_id"))


if __name__ == "__main__":
    asyncio.run(main())
