from __future__ import annotations

import json
from typing import Any

import groq

from app.core.config import Settings
from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
    LLMProvider,
    LLMProviderError,
    LLMResponse,
    LLMToolCall,
)


class GroqProvider(LLMProvider):
    """
    Groq implementation of Quanta's LLMProvider interface.

    This adapter translates between Quanta's provider-neutral LLM
    contract and Groq's OpenAI-compatible Chat Completions API.

    It does not:
    - execute tools
    - authorize users
    - execute transfers
    - manage Quanta state
    - access the UI Pay database
    """

    def __init__(
        self,
        *,
        settings: Settings,
        client: groq.AsyncGroq | None = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY is required for GroqProvider.")

            self._client = groq.AsyncGroq(
                api_key=settings.GROQ_API_KEY,
                timeout=settings.GROQ_TIMEOUT_SECONDS,
                max_retries=settings.GROQ_MAX_RETRIES,
            )

        self._model = settings.GROQ_MODEL
        self._max_tokens = settings.GROQ_MAX_TOKENS
        self._disable_parallel_tool_use = settings.GROQ_DISABLE_PARALLEL_TOOL_USE
        self._temperature = settings.GROQ_TEMPERATURE

    async def generate(
        self,
        *,
        messages: list[LLMMessage],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        try:
            request_messages = self._build_messages(
                messages=messages,
                system_prompt=system_prompt,
            )

            request_kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": request_messages,
                "max_completion_tokens": self._max_tokens,
                "temperature": self._temperature,
            }

            if tools:
                request_kwargs["tools"] = self._normalize_tools(tools)

                if self._disable_parallel_tool_use:
                    request_kwargs["parallel_tool_calls"] = False

            response = await self._client.chat.completions.create(
                **request_kwargs,
            )

            return self._normalize_response(response)

        except groq.AuthenticationError as exc:
            raise LLMProviderError(
                "Groq authentication failed.",
                code="GROQ_AUTHENTICATION_ERROR",
            ) from exc

        except groq.PermissionDeniedError as exc:
            raise LLMProviderError(
                "Groq permission was denied.",
                code="GROQ_PERMISSION_ERROR",
            ) from exc

        except groq.RateLimitError as exc:
            raise LLMProviderError(
                "Groq rate limit was exceeded.",
                code="GROQ_RATE_LIMIT",
                retryable=True,
            ) from exc

        except groq.APITimeoutError as exc:
            raise LLMProviderError(
                "Groq request timed out.",
                code="GROQ_TIMEOUT",
                retryable=True,
            ) from exc

        except groq.APIConnectionError as exc:
            raise LLMProviderError(
                "Groq could not be reached.",
                code="GROQ_CONNECTION_ERROR",
                retryable=True,
            ) from exc

        except groq.InternalServerError as exc:
            raise LLMProviderError(
                "Groq returned an internal server error.",
                code="GROQ_SERVER_ERROR",
                retryable=True,
            ) from exc

        except groq.BadRequestError as exc:
            raise LLMProviderError(
                "Groq rejected the request.",
                code="GROQ_BAD_REQUEST",
            ) from exc

        except groq.APIStatusError as exc:
            raise LLMProviderError(
                "Groq returned an API error.",
                code="GROQ_API_ERROR",
            ) from exc

    @staticmethod
    def _build_messages(
        *,
        messages: list[LLMMessage],
        system_prompt: str | None,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        if system_prompt:
            result.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        for message in messages:
            if message.role == LLMMessageRole.SYSTEM:
                raise ValueError("System messages must be passed through system_prompt.")

            if message.role == LLMMessageRole.USER:
                if not message.content:
                    raise ValueError("User messages must contain content.")

                result.append(
                    {
                        "role": "user",
                        "content": message.content,
                    }
                )
                continue

            if message.role == LLMMessageRole.ASSISTANT:
                if not message.content and not message.tool_calls:
                    raise ValueError("Assistant messages must contain content or tool calls.")

                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                }

                if message.content:
                    assistant_message["content"] = message.content

                if message.tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.name,
                                "arguments": _serialize_arguments(tool_call.arguments),
                            },
                        }
                        for tool_call in message.tool_calls
                    ]

                result.append(assistant_message)
                continue

            if message.role == LLMMessageRole.TOOL:
                if not message.tool_call_id:
                    raise ValueError("Tool messages require tool_call_id.")

                if message.content is None:
                    raise ValueError("Tool messages require content.")

                result.append(
                    {
                        "role": "tool",
                        "tool_call_id": message.tool_call_id,
                        "content": message.content,
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
            if tool.get("type") == "function" and "function" in tool:
                normalized.append(tool)
                continue

            name = tool.get("name")
            description = tool.get("description", "")
            parameters = tool.get("input_schema") or tool.get("parameters") or {}

            normalized.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": parameters,
                    },
                }
            )

        return normalized

    @staticmethod
    def _normalize_response(
        response: Any,
    ) -> LLMResponse:
        message = response.choices[0].message

        tool_calls: list[LLMToolCall] = []

        for tool_call in message.tool_calls or []:
            arguments = tool_call.function.arguments

            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError as exc:
                    raise LLMProviderError(
                        "Groq returned invalid tool arguments.",
                        code="GROQ_INVALID_TOOL_ARGUMENTS",
                    ) from exc

            tool_calls.append(
                LLMToolCall(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=arguments,
                )
            )

        provider_metadata: dict[str, Any] = {
            "model": response.model,
            "finish_reason": response.choices[0].finish_reason,
        }

        if response.usage is not None:
            provider_metadata["usage"] = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            }

        if getattr(response, "id", None):
            provider_metadata["request_id"] = response.id

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=response.choices[0].finish_reason,
            provider_metadata=provider_metadata,
        )


def _serialize_arguments(arguments: dict[str, Any]) -> str:
    import json

    return json.dumps(
        arguments,
        separators=(",", ":"),
    )
