from __future__ import annotations

from typing import Any

import anthropic

from app.core.config import Settings
from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
    LLMProvider,
    LLMProviderError,
    LLMResponse,
    LLMToolCall,
)


class ClaudeProvider(LLMProvider):
    """
    Anthropic implementation of Quanta's provider-neutral LLM interface.

    This adapter translates Quanta's normalized LLM messages and tool
    definitions into Anthropic's Messages API format and normalizes
    Anthropic responses back into Quanta models.

    The provider does not execute tools or make authorization decisions.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY is required for ClaudeProvider.")

            self._client = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                timeout=settings.CLAUDE_TIMEOUT_SECONDS,
                max_retries=settings.CLAUDE_MAX_RETRIES,
            )

        self._model = settings.CLAUDE_MODEL
        self._max_tokens = settings.CLAUDE_MAX_TOKENS

    async def generate(
        self,
        *,
        messages: list[LLMMessage],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        try:
            request_kwargs: dict[str, Any] = {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "messages": self._build_messages(messages),
            }

            if system_prompt:
                request_kwargs["system"] = system_prompt

            if tools:
                request_kwargs["tools"] = self._normalize_tools(tools)

            response = await self._client.messages.create(
                **request_kwargs,
            )

            return self._normalize_response(response)

        except anthropic.AuthenticationError as exc:
            raise LLMProviderError(
                "Claude authentication failed.",
                code="CLAUDE_AUTHENTICATION_ERROR",
            ) from exc

        except anthropic.PermissionDeniedError as exc:
            raise LLMProviderError(
                "Claude permission was denied.",
                code="CLAUDE_PERMISSION_ERROR",
            ) from exc

        except anthropic.RateLimitError as exc:
            raise LLMProviderError(
                "Claude rate limit was exceeded.",
                code="CLAUDE_RATE_LIMIT",
                retryable=True,
            ) from exc

        except anthropic.APITimeoutError as exc:
            raise LLMProviderError(
                "Claude request timed out.",
                code="CLAUDE_TIMEOUT",
                retryable=True,
            ) from exc

        except anthropic.APIConnectionError as exc:
            raise LLMProviderError(
                "Claude could not be reached.",
                code="CLAUDE_CONNECTION_ERROR",
                retryable=True,
            ) from exc

        except anthropic.InternalServerError as exc:
            raise LLMProviderError(
                "Claude returned an internal server error.",
                code="CLAUDE_SERVER_ERROR",
                retryable=True,
            ) from exc

        except anthropic.BadRequestError as exc:
            raise LLMProviderError(
                "Claude rejected the request.",
                code="CLAUDE_BAD_REQUEST",
            ) from exc

        except anthropic.APIStatusError as exc:
            raise LLMProviderError(
                "Claude returned an API error.",
                code="CLAUDE_API_ERROR",
            ) from exc

    @staticmethod
    def _build_messages(
        messages: list[LLMMessage],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        for message in messages:
            if message.role == LLMMessageRole.SYSTEM:
                raise ValueError("System messages must be passed through system_prompt.")

            if message.role == LLMMessageRole.USER:
                result.append(
                    {
                        "role": "user",
                        "content": message.content,
                    }
                )
                continue

            if message.role == LLMMessageRole.ASSISTANT:
                content: list[dict[str, Any]] = []

                if message.content:
                    content.append(
                        {
                            "type": "text",
                            "text": message.content,
                        }
                    )

                for tool_call in message.tool_calls:
                    content.append(
                        {
                            "type": "tool_use",
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "input": tool_call.arguments,
                        }
                    )

                result.append(
                    {
                        "role": "assistant",
                        "content": content,
                    }
                )
                continue

            if message.role == LLMMessageRole.TOOL:
                result.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.tool_call_id,
                                "content": message.content,
                            }
                        ],
                    }
                )
                continue

            raise ValueError(f"Unsupported LLM message role: {message.role}")

        return result

    @staticmethod
    def _normalize_tools(
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []

        for tool in tools:
            if "name" not in tool and ("function" not in tool or "name" not in tool["function"]):
                raise ValueError("Claude tool definition requires name.")

            name = tool.get("name") or tool.get("function", {}).get("name")
            description = tool.get("description") or tool.get("function", {}).get("description", "")
            input_schema = (
                tool.get("input_schema")
                or tool.get("parameters")
                or tool.get("function", {}).get("parameters")
            )

            if not input_schema:
                raise ValueError(f"Claude tool '{name}' requires input_schema.")

            normalized.append(
                {
                    "name": name,
                    "description": description,
                    "input_schema": input_schema,
                }
            )

        return normalized

    @staticmethod
    def _normalize_response(
        response: Any,
    ) -> LLMResponse:
        content: str | None = None
        tool_calls: list[LLMToolCall] = []

        text_parts: list[str] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)

            elif block.type == "tool_use":
                tool_calls.append(
                    LLMToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        if text_parts:
            content = "\n".join(text_parts)

        provider_metadata: dict[str, Any] = {
            "model": response.model,
            "stop_reason": response.stop_reason,
        }

        if response.usage is not None:
            provider_metadata["usage"] = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }

            if getattr(response.usage, "cache_read_input_tokens", None) is not None:
                provider_metadata["usage"]["cache_read_input_tokens"] = (
                    response.usage.cache_read_input_tokens
                )

            if getattr(response.usage, "cache_creation_input_tokens", None) is not None:
                provider_metadata["usage"]["cache_creation_input_tokens"] = (
                    response.usage.cache_creation_input_tokens
                )

        if getattr(response, "_request_id", None):
            provider_metadata["request_id"] = response._request_id

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason,
            provider_metadata=provider_metadata,
        )
