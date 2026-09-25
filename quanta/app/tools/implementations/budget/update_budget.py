from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.context import RequestContext
from app.domain.budget.models import UpdateReason
from app.schemas.budget import BudgetAllocationSchema, GoalAllocationSchema, IncomePlanSchema
from app.services.budget_service import BudgetService
from app.tools.base import Tool, ToolClassification, ToolResult


class UpdateBudgetInput(BaseModel):
    """Input parameters for updating a budget."""

    model_config = ConfigDict(frozen=True)

    budget_id: str = Field(min_length=1, description="ID of the budget to update.")
    as_of_date: date | None = Field(
        default=None, description="Effective date of change (defaults to today)."
    )
    income_update: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), description="Updated expected income."
    )
    allocation_updates: list[dict[str, Any]] | None = Field(
        default=None, description="Updated category allocations."
    )
    goal_updates: list[dict[str, Any]] | None = Field(
        default=None, description="Updated goal allocations."
    )
    update_reason: UpdateReason = Field(
        default=UpdateReason.OTHER, description="Reason for budget update."
    )


class UpdateBudgetOutput(BaseModel):
    id: str
    start_date: date
    end_date: date
    currency: str = "NGN"
    version: int
    status: str
    previous_version_id: str | None
    update_reason: str
    income_plan: IncomePlanSchema
    allocations: list[BudgetAllocationSchema]
    goal_allocations: list[GoalAllocationSchema]
    total_allocated_expenses: Decimal
    total_allocated_goals: Decimal
    total_unallocated_income: Decimal


class UpdateBudgetTool(Tool[UpdateBudgetInput, UpdateBudgetOutput]):
    name = "update_budget"
    description = (
        "Update an existing active budget by creating a new version. Preserves the original start_date and end_date. "
        "Recalculates allocations for the remaining budget period without restarting the period."
    )
    classification = ToolClassification.WRITE
    input_model = UpdateBudgetInput
    output_model = UpdateBudgetOutput

    def __init__(self, *, service: BudgetService) -> None:
        self._service = service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: UpdateBudgetInput,
    ) -> ToolResult:
        try:
            new_budget, _prev_budget = await self._service.update_budget(
                user_id=context.user_id,
                budget_id=arguments.budget_id,
                as_of_date=arguments.as_of_date,
                income_update=arguments.income_update,
                allocation_updates=arguments.allocation_updates,
                goal_updates=arguments.goal_updates,
                update_reason=arguments.update_reason,
            )
            output = UpdateBudgetOutput(
                id=new_budget.id,
                start_date=new_budget.start_date,
                end_date=new_budget.end_date,
                currency=new_budget.currency,
                version=new_budget.version,
                status=new_budget.status.value,
                previous_version_id=new_budget.previous_version_id,
                update_reason=new_budget.update_reason.value,
                income_plan=IncomePlanSchema(
                    expected_income=new_budget.income_plan.expected_income,
                    income_sources=new_budget.income_plan.income_sources,
                ),
                allocations=[
                    BudgetAllocationSchema(
                        category=a.category,
                        allocated_amount=a.allocated_amount,
                        notes=a.notes,
                    )
                    for a in new_budget.allocations
                ],
                goal_allocations=[
                    GoalAllocationSchema(
                        goal_id=g.goal_id,
                        goal_name=g.goal_name,
                        allocated_amount=g.allocated_amount,
                    )
                    for g in new_budget.goal_allocations
                ],
                total_allocated_expenses=new_budget.total_allocated_expenses,
                total_allocated_goals=new_budget.total_allocated_goals,
                total_unallocated_income=new_budget.total_unallocated_income,
            )
            return ToolResult(
                success=True,
                data=output.model_dump(mode="json"),
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                error_code="UPDATE_BUDGET_FAILED",
                error_message=str(exc),
            )
