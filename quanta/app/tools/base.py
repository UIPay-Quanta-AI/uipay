from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.core.context import RequestContext


class ToolClassification(str, Enum):
    PUBLIC = "public"
    READ = "read"
    SENSITIVE_READ = "sensitive_read"
    WRITE = "write"
    FINANCIAL = "financial"
    SYSTEM = "system"


class ToolResult(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


class ToolError(Exception):
    """Base exception for tool-layer failures."""


class ToolNotFoundError(ToolError):
    pass


class ToolNotAllowedError(ToolError):
    pass


class ToolArgumentError(ToolError):
    pass


class ToolExecutionError(ToolError):
    pass


class Tool[InputModelT: BaseModel, OutputModelT: BaseModel](ABC):
    """
    Base contract for every Quanta tool.

    A tool represents one narrowly scoped capability that can be requested
    by the orchestration layer.
    """

    name: str
    description: str
    classification: ToolClassification
    input_model: type[InputModelT]
    output_model: type[OutputModelT]

    @abstractmethod
    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: InputModelT,
    ) -> ToolResult:
        """
        Execute the tool using trusted request context and validated arguments.
        """
        raise NotImplementedError

    def definition(self) -> dict[str, Any]:
        """
        Return the tool definition exposed to the LLM.

        The LLM receives capability information, but never receives
        authorization information such as user identity or credentials.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }
