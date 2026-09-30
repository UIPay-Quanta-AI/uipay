"""
Tool implementation for explicitly completing a user's financial goal.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.context import RequestContext
from app.services.goal_service import GoalService, GoalServiceError
from app.tools.base import Tool, ToolClassification, ToolResult


class CompleteGoalInput(BaseModel):
    """
    Input schema for complete_goal tool.
    user_id is strictly overridden by RequestContext.user_id.
    """

    model_config = ConfigDict(frozen=True)

    goal_identifier: str = Field(
        min_length=1,
        description="The ID or exact name of the goal to complete.",
    )


class CompleteGoalOutput(BaseModel):
    """Output schema for complete_goal tool."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    status: str
    message: str


class CompleteGoalTool(Tool[CompleteGoalInput, CompleteGoalOutput]):
    name = "complete_goal"
    description = (
        "Explicitly mark a financial goal as completed when requested by the user. "
        "Requires explicit user intent."
    )
    classification = ToolClassification.WRITE
    input_model = CompleteGoalInput
    output_model = CompleteGoalOutput

    def __init__(self, *, goal_service: GoalService) -> None:
        self._goal_service = goal_service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: CompleteGoalInput,
    ) -> ToolResult:
        try:
            goal = await self._goal_service.complete_goal(
                user_id=context.user_id,
                goal_identifier=arguments.goal_identifier,
            )
            output = CompleteGoalOutput(
                id=goal.id,
                name=goal.name,
                status=goal.status.value if hasattr(goal.status, "value") else str(goal.status),
                message=f"Goal '{goal.name}' has been successfully completed!",
            )
            return ToolResult(
                success=True,
                data=output.model_dump(mode="json"),
            )
        except GoalServiceError as exc:
            return ToolResult(
                success=False,
                error_code="GOAL_SERVICE_ERROR",
                error_message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                error_code="COMPLETE_GOAL_FAILED",
                error_message=str(exc),
            )
