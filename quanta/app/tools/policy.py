from __future__ import annotations

from dataclasses import dataclass

from app.core.context import RequestContext
from app.schemas.states import QuantaState
from app.tools.base import Tool, ToolClassification, ToolNotAllowedError


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    """
    Deterministic policy enforcement for tool execution.
    """

    require_authenticated_user: bool = True

    def check(
        self,
        *,
        tool: Tool,
        context: RequestContext,
        state: QuantaState,
    ) -> None:
        self._check_authentication(context)
        self._check_classification(tool)
        self._check_state(
            tool=tool,
            state=state,
        )

    def _check_authentication(
        self,
        context: RequestContext,
    ) -> None:
        if not self.require_authenticated_user:
            return

        if not context.user_id.strip():
            raise ToolNotAllowedError("Authenticated user context is required.")

    def _check_classification(
        self,
        tool: Tool,
    ) -> None:
        if tool.classification == ToolClassification.SYSTEM:
            raise ToolNotAllowedError(
                f"System tool cannot be requested through normal orchestration: {tool.name}"
            )

    def _check_state(
        self,
        *,
        tool: Tool,
        state: QuantaState,
    ) -> None:
        """
        Basic state enforcement.

        More granular tool-specific state policies can be added later,
        but financial execution must never be inferred from tool names
        alone.
        """

        if state in {
            QuantaState.SUCCESS,
            QuantaState.CANCELLED,
            QuantaState.EXPIRED,
        }:
            raise ToolNotAllowedError(
                f"Tool execution is not allowed in terminal state: {state.value}"
            )
