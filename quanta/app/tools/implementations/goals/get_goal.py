from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.context import RequestContext
from app.services.goal_service import GoalService
from app.tools.base import Tool, ToolClassification, ToolResult


class GetGoalInput(BaseModel):
    """Input parameters for searching/getting a specific goal."""

    model_config = ConfigDict(frozen=True)

    goal_identifier: str = Field(
        min_length=1,
        description="ID or name of the goal to retrieve (e.g., 'goal-123' or 'laptop').",
    )


class GetGoalOutput(BaseModel):
    id: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    remaining_amount: Decimal
    target_date: date | None = None
    currency: str = "NGN"
    status: str


class GetGoalTool(Tool[GetGoalInput, GetGoalOutput]):
    name = "get_goal"
    description = "Retrieve details for a specific financial goal by ID or name, including remaining amount to save."
    classification = ToolClassification.SENSITIVE_READ
    input_model = GetGoalInput
    output_model = GetGoalOutput

    def __init__(self, *, service: GoalService) -> None:
        self._service = service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: GetGoalInput,
    ) -> ToolResult:
        try:
            goal = await self._service.get_goal(
                user_id=context.user_id,
                goal_identifier=arguments.goal_identifier,
            )
            output = GetGoalOutput(
                id=goal.id,
                name=goal.name,
                target_amount=goal.target_amount,
                current_amount=goal.current_amount,
                remaining_amount=goal.remaining_amount,
                target_date=goal.target_date,
                currency=goal.currency,
                status=goal.status.value,
            )
            return ToolResult(
                success=True,
                data=output.model_dump(mode="json"),
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                error_code="GET_GOAL_FAILED",
                error_message=str(exc),
            )
