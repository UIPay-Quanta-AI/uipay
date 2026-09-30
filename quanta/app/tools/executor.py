from __future__ import annotations

import time
from typing import Any

from pydantic import ValidationError

from app.core.context import RequestContext
from app.core.observability import log_security_decision, log_tool_execution
from app.schemas.states import QuantaState
from app.tools.base import (
    ToolArgumentError,
    ToolExecutionError,
    ToolResult,
)
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry


class ToolExecutor:
    """
    Security and execution boundary for Quanta tools.

    Claude requests capabilities through tool calls, but this executor
    determines whether those capabilities can actually be invoked.
    """

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        policy: ToolPolicy,
    ) -> None:
        self._registry = registry
        self._policy = policy

    async def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        context: RequestContext,
        state: QuantaState,
    ) -> ToolResult:
        tool = self._registry.get(tool_name)

        try:
            self._policy.check(
                tool=tool,
                context=context,
                state=state,
            )
            log_security_decision(
                "tool_policy", context, allowed=True, reason=f"Policy passed for {tool_name}"
            )
        except Exception as exc:
            log_security_decision("tool_policy", context, allowed=False, reason=str(exc))
            raise

        validated_arguments = self._validate_arguments(
            tool=tool,
            arguments=arguments,
        )

        start_time = time.perf_counter()
        try:
            result = await tool.execute(
                context=context,
                arguments=validated_arguments,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            log_tool_execution(
                tool_name,
                context,
                success=False,
                latency_ms=latency_ms,
                error=str(exc),
            )
            if isinstance(exc, ToolExecutionError):
                raise

            raise ToolExecutionError(f"Tool execution failed: {tool_name}") from exc

        validated_result = self._validate_result(
            tool=tool,
            result=result,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        log_tool_execution(
            tool_name,
            context,
            success=validated_result.success,
            latency_ms=latency_ms,
            error=validated_result.error_message,
        )

        return self._sanitize_result(validated_result)

    @staticmethod
    def _validate_arguments(
        *,
        tool: Any,
        arguments: dict[str, Any],
    ) -> Any:
        try:
            return tool.input_model.model_validate(arguments)
        except ValidationError as exc:
            raise ToolArgumentError(f"Invalid arguments for tool: {tool.name}") from exc

    @staticmethod
    def _validate_result(
        *,
        tool: Any,
        result: ToolResult,
    ) -> ToolResult:
        if not isinstance(result, ToolResult):
            raise ToolExecutionError(f"Tool returned an invalid result: {tool.name}")

        if not result.success:
            return result

        if result.data is None:
            raise ToolExecutionError(f"Successful tool returned no data: {tool.name}")

        try:
            output = tool.output_model.model_validate(result.data)
        except ValidationError as exc:
            raise ToolExecutionError(f"Tool returned invalid data: {tool.name}") from exc

        return ToolResult(
            success=True,
            data=output.model_dump(mode="json"),
        )

    @staticmethod
    def _sanitize_result(
        result: ToolResult,
    ) -> ToolResult:
        """
        Final boundary before a tool result can return to orchestration/LLM.

        Provider/backend implementations must not be allowed to accidentally
        return secrets or unrestricted internal data.
        """

        if result.data is None:
            return result

        return ToolResult(
            success=result.success,
            data=result.data,
            error_code=result.error_code,
            error_message=result.error_message,
        )
