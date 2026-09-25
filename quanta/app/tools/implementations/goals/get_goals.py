from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.context import RequestContext
from app.domain.goals.models import GoalStatus
from app.services.goal_service import GoalService
from app.tools.base import Tool, ToolClassification, ToolResult


class GetGoalsInput(BaseModel):
    """Input for retrieving active/all user financial goals."""

    model_config = ConfigDict(frozen=True)

    status: GoalStatus | None = Field(
        default=None, description="Optional status filter (active, completed, paused, cancelled)."
    )


class GoalItem(BaseModel):
    id: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    remaining_amount: Decimal
    target_date: date | None = None
    currency: str = "NGN"
    status: str


class GetGoalsOutput(BaseModel):
    goals: list[GoalItem]
    total_count: int


class GetGoalsTool(Tool[GetGoalsInput, GetGoalsOutput]):
    name = "get_goals"
    description = "Retrieve the authenticated user's financial goals and progress details."
    classification = ToolClassification.SENSITIVE_READ
    input_model = GetGoalsInput
    output_model = GetGoalsOutput

    def __init__(self, *, service: GoalService) -> None:
        self._service = service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: GetGoalsInput,
    ) -> ToolResult:
        try:
            goals = await self._service.get_goals(
                user_id=context.user_id,
                status=arguments.status,
            )
            items = [
                GoalItem(
                    id=g.id,
                    name=g.name,
                    target_amount=g.target_amount,
                    current_amount=g.current_amount,
                    remaining_amount=g.remaining_amount,
                    target_date=g.target_date,
                    currency=g.currency,
                    status=g.status.value,
                )
                for g in goals
            ]
            output = GetGoalsOutput(
                goals=items,
                total_count=len(items),
            )
            return ToolResult(
                success=True,
                data=output.model_dump(mode="json"),
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                error_code="GET_GOALS_FAILED",
                error_message=str(exc),
            )
