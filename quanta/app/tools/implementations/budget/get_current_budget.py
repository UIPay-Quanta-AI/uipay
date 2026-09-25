from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.core.context import RequestContext
from app.schemas.budget import BudgetAllocationSchema, GoalAllocationSchema, IncomePlanSchema
from app.services.budget_service import BudgetService
from app.tools.base import Tool, ToolClassification, ToolResult


class GetCurrentBudgetInput(BaseModel):
    """Input for retrieving current active budget."""

    model_config = ConfigDict(frozen=True)


class GetCurrentBudgetOutput(BaseModel):
    budget_exists: bool
    id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    currency: str = "NGN"
    version: int | None = None
    status: str | None = None
    income_plan: IncomePlanSchema | None = None
    allocations: list[BudgetAllocationSchema] = []
    goal_allocations: list[GoalAllocationSchema] = []
    total_allocated_expenses: Decimal | None = None
    total_allocated_goals: Decimal | None = None
    total_unallocated_income: Decimal | None = None


class GetCurrentBudgetTool(Tool[GetCurrentBudgetInput, GetCurrentBudgetOutput]):
    name = "get_current_budget"
    description = (
        "Retrieve the authenticated user's current active budget details and category allocations."
    )
    classification = ToolClassification.SENSITIVE_READ
    input_model = GetCurrentBudgetInput
    output_model = GetCurrentBudgetOutput

    def __init__(self, *, service: BudgetService) -> None:
        self._service = service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: GetCurrentBudgetInput,
    ) -> ToolResult:
        try:
            budget = await self._service.get_current_budget(user_id=context.user_id)
            if not budget:
                output = GetCurrentBudgetOutput(budget_exists=False)
            else:
                output = GetCurrentBudgetOutput(
                    budget_exists=True,
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
                error_code="GET_CURRENT_BUDGET_FAILED",
                error_message=str(exc),
            )
