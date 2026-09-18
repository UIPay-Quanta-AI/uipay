from __future__ import annotations

import asyncio
import sys

from app.core.config import Settings
from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
)
from app.providers.llm.claude import ClaudeProvider
from app.providers.llm.groq import GroqProvider


async def chat_with_provider(provider_name: str) -> None:
    settings = Settings()

    if provider_name == "groq":
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not configured.")
        provider = GroqProvider(settings=settings)
    elif provider_name == "claude":
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")
        provider = ClaudeProvider(settings=settings)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}. Available: groq, claude.")

    messages: list[LLMMessage] = []

    print(f"--- {provider_name.upper()} Interactive Chat ---")
    print("Type 'exit' or 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if user_input.lower() in {"exit", "quit"}:
            break

        if not user_input:
            continue

        messages.append(
            LLMMessage(
                role=LLMMessageRole.USER,
                content=user_input,
            )
        )

        response = await provider.generate(
            messages=messages,
            system_prompt=(
                "You are Quanta, a financial assistant. Answer naturally and concisely."
            ),
        )

        if response.content:
            print(f"Quanta: {response.content}")
            messages.append(
                LLMMessage(
                    role=LLMMessageRole.ASSISTANT,
                    content=response.content,
                )
            )

        if response.tool_calls:
            print("\n[Tool calls requested]:")
            for tool_call in response.tool_calls:
                print(f"  Name: {tool_call.name}")
                print(f"  ID: {tool_call.id}")
                print(f"  Arguments: {tool_call.arguments}")

        print()


async def main() -> None:
    provider = sys.argv[1].lower() if len(sys.argv) > 1 else "groq"
    await chat_with_provider(provider)


if __name__ == "__main__":
    asyncio.run(main())
