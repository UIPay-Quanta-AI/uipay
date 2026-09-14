from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.providers.base import Provider, ProviderError


class LLMMessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMMessage(BaseModel):
    """
    A message exchanged with an LLM provider.
    """

    role: LLMMessageRole
    content: str = Field(min_length=1)


class LLMToolCall(BaseModel):
    """
    A structured tool request returned by an LLM.
    """

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """
    Provider-neutral response returned by an LLM.
    """

    content: str | None = None
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    finish_reason: str | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class LLMProviderError(ProviderError):
    """
    Raised when an LLM provider fails.
    """


class LLMProvider(Provider):
    """
    Provider-neutral interface for large language model providers.
    """

    @abstractmethod
    async def generate(
        self,
        *,
        messages: list[LLMMessage],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """
        Generate a response from the configured LLM provider.

        Implementations must normalize provider-specific responses
        into LLMResponse.
        """
        raise NotImplementedError
