from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.context import RequestContext
from app.schemas.budget import BudgetAllocationSchema, GoalAllocationSchema, IncomePlanSchema
from app.services.budget_service import BudgetService
from app.tools.base import Tool, ToolClassification, ToolResult


class GenerateBudgetInput(BaseModel):
    """Input for generating a new budget."""

    model_config = ConfigDict(frozen=True)

    start_date: date = Field(description="Start date of the budget period.")
    end_date: date = Field(description="End date of the budget period.")
    income_override: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), description="Optional income override in NGN."
    )
    custom_allocations: list[dict[str, Any]] | None = Field(
        default=None, description="Optional custom category allocations."
    )


class GenerateBudgetOutput(BaseModel):
    id: str
    start_date: date
    end_date: date
    currency: str = "NGN"
    version: int
    status: str
    income_plan: IncomePlanSchema
    allocations: list[BudgetAllocationSchema]
    goal_allocations: list[GoalAllocationSchema]
    total_allocated_expenses: Decimal
    total_allocated_goals: Decimal
    total_unallocated_income: Decimal


class GenerateBudgetTool(Tool[GenerateBudgetInput, GenerateBudgetOutput]):
    name = "generate_budget"
    description = (
        "Generate a deterministic financial budget for a specified date range (start_date to end_date). "
        "Integrates Financial Profile income/expenses, active goals, and transaction context if available."
    )
    classification = ToolClassification.WRITE
    input_model = GenerateBudgetInput
    output_model = GenerateBudgetOutput

    def __init__(self, *, service: BudgetService) -> None:
        self._service = service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: GenerateBudgetInput,
    ) -> ToolResult:
        try:
            budget = await self._service.generate_budget(
                user_id=context.user_id,
                start_date=arguments.start_date,
                end_date=arguments.end_date,
                income_override=arguments.income_override,
                custom_allocations=arguments.custom_allocations,
            )
            output = GenerateBudgetOutput(
                id=budget.id,
                start_date=budget.start_date,
                end_date=budget.end_date,
                currency=budget.currency,
                version=budget.version,
                status=budget.status.value,
                income_plan=IncomePlanSchema(
                    expected_income=budget.income_plan.expected_income,
                    income_sources=budget.income_plan.income_sources,
                ),
                allocations=[
                    BudgetAllocationSchema(
                        category=a.category,
                        allocated_amount=a.allocated_amount,
                        notes=a.notes,
                    )
                    for a in budget.allocations
                ],
                goal_allocations=[
                    GoalAllocationSchema(
                        goal_id=g.goal_id,
                        goal_name=g.goal_name,
                        allocated_amount=g.allocated_amount,
                    )
                    for g in budget.goal_allocations
                ],
                total_allocated_expenses=budget.total_allocated_expenses,
                total_allocated_goals=budget.total_allocated_goals,
                total_unallocated_income=budget.total_unallocated_income,
            )
            return ToolResult(
                success=True,
                data=output.model_dump(mode="json"),
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                error_code="GENERATE_BUDGET_FAILED",
                error_message=str(exc),
            )
