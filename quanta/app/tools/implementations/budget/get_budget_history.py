from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.core.context import RequestContext
from app.schemas.budget import BudgetAllocationSchema, GoalAllocationSchema, IncomePlanSchema
from app.services.budget_service import BudgetService
from app.tools.base import Tool, ToolClassification, ToolResult


class GetBudgetHistoryInput(BaseModel):
    """Input for retrieving full version history of user budgets."""

    model_config = ConfigDict(frozen=True)


class BudgetHistoryItem(BaseModel):
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


class GetBudgetHistoryOutput(BaseModel):
    budgets: list[BudgetHistoryItem]
    total_count: int


class GetBudgetHistoryTool(Tool[GetBudgetHistoryInput, GetBudgetHistoryOutput]):
    name = "get_budget_history"
    description = "Retrieve the full version history of budgets for the authenticated user."
    classification = ToolClassification.SENSITIVE_READ
    input_model = GetBudgetHistoryInput
    output_model = GetBudgetHistoryOutput

    def __init__(self, *, service: BudgetService) -> None:
        self._service = service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: GetBudgetHistoryInput,
    ) -> ToolResult:
        try:
            history = await self._service.get_budget_history(user_id=context.user_id)
            items = [
                BudgetHistoryItem(
                    id=b.id,
                    start_date=b.start_date,
                    end_date=b.end_date,
                    currency=b.currency,
                    version=b.version,
                    status=b.status.value,
                    previous_version_id=b.previous_version_id,
                    update_reason=b.update_reason.value,
                    income_plan=IncomePlanSchema(
                        expected_income=b.income_plan.expected_income,
                        income_sources=b.income_plan.income_sources,
                    ),
                    allocations=[
                        BudgetAllocationSchema(
                            category=a.category,
                            allocated_amount=a.allocated_amount,
                            notes=a.notes,
                        )
                        for a in b.allocations
                    ],
                    goal_allocations=[
                        GoalAllocationSchema(
                            goal_id=g.goal_id,
                            goal_name=g.goal_name,
                            allocated_amount=g.allocated_amount,
                        )
                        for g in b.goal_allocations
                    ],
                    total_allocated_expenses=b.total_allocated_expenses,
                    total_allocated_goals=b.total_allocated_goals,
                    total_unallocated_income=b.total_unallocated_income,
                )
                for b in history
            ]
            output = GetBudgetHistoryOutput(
                budgets=items,
                total_count=len(items),
            )
            return ToolResult(
                success=True,
                data=output.model_dump(mode="json"),
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                error_code="GET_BUDGET_HISTORY_FAILED",
                error_message=str(exc),
            )
