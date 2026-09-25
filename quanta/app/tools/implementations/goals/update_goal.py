from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.context import RequestContext
from app.domain.goals.models import GoalStatus
from app.services.goal_service import GoalService
from app.tools.base import Tool, ToolClassification, ToolResult


class UpdateGoalInput(BaseModel):
    """Input parameters for updating a financial goal."""

    model_config = ConfigDict(frozen=True)

    goal_identifier: str = Field(min_length=1, description="ID or name of the goal to update.")
    name: str | None = Field(default=None, description="New name for the goal.")
    target_amount: Decimal | None = Field(
        default=None, gt=Decimal("0.00"), description="Updated target amount."
    )
    current_amount: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), description="Updated saved/current amount."
    )
    target_date: date | None = Field(default=None, description="Updated target date.")
    status: GoalStatus | None = Field(
        default=None, description="Updated goal status (active, completed, paused, cancelled)."
    )


class UpdateGoalOutput(BaseModel):
    id: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    remaining_amount: Decimal
    target_date: date | None = None
    currency: str = "NGN"
    status: str


class UpdateGoalTool(Tool[UpdateGoalInput, UpdateGoalOutput]):
    name = "update_goal"
    description = (
        "Update details of an existing financial goal (e.g. target amount, saved amount, status)."
    )
    classification = ToolClassification.WRITE
    input_model = UpdateGoalInput
    output_model = UpdateGoalOutput

    def __init__(self, *, service: GoalService) -> None:
        self._service = service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: UpdateGoalInput,
    ) -> ToolResult:
        updates = arguments.model_dump(exclude={"goal_identifier"}, exclude_unset=True)
        if not updates:
            return ToolResult(
                success=False,
                error_code="INVALID_ARGUMENTS",
                error_message="At least one goal field must be provided for update.",
            )

        try:
            goal = await self._service.update_goal(
                user_id=context.user_id,
                goal_identifier=arguments.goal_identifier,
                updates=updates,
            )
            output = UpdateGoalOutput(
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
                error_code="UPDATE_GOAL_FAILED",
                error_message=str(exc),
            )
