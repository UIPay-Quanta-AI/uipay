from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.providers.base import Provider, ProviderError


class LLMMessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMToolCall(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMMessage(BaseModel):
    role: LLMMessageRole
    content: str | None = None
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None

    @model_validator(mode="after")
    def validate_role_contract(self) -> LLMMessage:
        has_content = self.content is not None and bool(self.content.strip())
        has_tool_calls = bool(self.tool_calls)
        has_tool_call_id = bool(self.tool_call_id)

        if self.role == LLMMessageRole.SYSTEM:
            if not has_content:
                raise ValueError("System messages must contain non-empty content.")

            if has_tool_calls:
                raise ValueError("System messages cannot contain tool calls.")

            if has_tool_call_id:
                raise ValueError("System messages cannot contain tool_call_id.")

        elif self.role == LLMMessageRole.USER:
            if not has_content:
                raise ValueError("User messages must contain non-empty content.")

            if has_tool_calls:
                raise ValueError("User messages cannot contain tool calls.")

            if has_tool_call_id:
                raise ValueError("User messages cannot contain tool_call_id.")

        elif self.role == LLMMessageRole.ASSISTANT:
            if not has_content and not has_tool_calls:
                raise ValueError("Assistant messages must contain content or tool calls.")

            if has_tool_call_id:
                raise ValueError("Assistant messages cannot contain tool_call_id.")

        elif self.role == LLMMessageRole.TOOL:
            if not has_content:
                raise ValueError("Tool messages must contain non-empty content.")

            if not has_tool_call_id:
                raise ValueError("Tool messages require tool_call_id.")

            if has_tool_calls:
                raise ValueError("Tool messages cannot contain tool calls.")

        return self


class LLMResponse(BaseModel):
    content: str | None = None
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    finish_reason: str | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class LLMProviderError(ProviderError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "LLM_PROVIDER_ERROR",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class LLMProvider(Provider):
    @abstractmethod
    async def generate(
        self,
        *,
        messages: list[LLMMessage],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        raise NotImplementedError
