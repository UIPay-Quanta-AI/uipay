from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.context import RequestContext
from app.services.goal_service import GoalService
from app.tools.base import Tool, ToolClassification, ToolResult


class CreateGoalInput(BaseModel):
    """Input parameters for creating a financial goal."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        min_length=1, description="Name or title of the goal (e.g. 'Laptop', 'Rent')."
    )
    target_amount: Decimal = Field(gt=Decimal("0.00"), description="Target amount to save in NGN.")
    target_date: date | None = Field(
        default=None, description="Optional target date to achieve goal."
    )


class CreateGoalOutput(BaseModel):
    id: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    remaining_amount: Decimal
    target_date: date | None = None
    currency: str = "NGN"
    status: str


class CreateGoalTool(Tool[CreateGoalInput, CreateGoalOutput]):
    name = "create_goal"
    description = (
        "Create a new financial goal for tracking savings targets (e.g., saving for a laptop, rent). "
        "Goals are for planning and tracking only. This tool does NOT execute transfers or payments."
    )
    classification = ToolClassification.WRITE
    input_model = CreateGoalInput
    output_model = CreateGoalOutput

    def __init__(self, *, service: GoalService) -> None:
        self._service = service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: CreateGoalInput,
    ) -> ToolResult:
        try:
            goal = await self._service.create_goal(
                user_id=context.user_id,
                name=arguments.name,
                target_amount=arguments.target_amount,
                target_date=arguments.target_date,
            )
            output = CreateGoalOutput(
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
                error_code="CREATE_GOAL_FAILED",
                error_message=str(exc),
            )
