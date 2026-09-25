from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.budget.models import BudgetStatus, UpdateReason


class BudgetAllocationSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str = Field(min_length=1)
    allocated_amount: Decimal = Field(ge=Decimal("0.00"))
    notes: str | None = None


class GoalAllocationSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    goal_id: str = Field(min_length=1)
    goal_name: str = Field(min_length=1)
    allocated_amount: Decimal = Field(ge=Decimal("0.00"))


class IncomePlanSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    expected_income: Decimal = Field(ge=Decimal("0.00"))
    income_sources: list[str] = Field(default_factory=list)


class BudgetSchema(BaseModel):
    """Boundary representation of a budget."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    start_date: date
    end_date: date
    currency: str = Field(default="NGN")
    version: int = Field(ge=1)
    status: BudgetStatus
    income_plan: IncomePlanSchema
    allocations: list[BudgetAllocationSchema]
    goal_allocations: list[GoalAllocationSchema]
    total_allocated_expenses: Decimal
    total_allocated_goals: Decimal
    total_unallocated_income: Decimal
    previous_version_id: str | None = None
    update_reason: UpdateReason
    created_at: datetime
    updated_at: datetime


class GenerateBudgetRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date
    income_override: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    notes: str | None = None


class UpdateBudgetRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    budget_id: str = Field(min_length=1)
    as_of_date: date | None = None
    income_update: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    allocation_updates: list[BudgetAllocationSchema] | None = None
    goal_updates: list[GoalAllocationSchema] | None = None
    update_reason: UpdateReason = UpdateReason.OTHER


class GenerateBudgetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    budget: BudgetSchema


class UpdateBudgetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    budget: BudgetSchema
    previous_version: BudgetSchema


class GetBudgetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    budget: BudgetSchema | None


class GetBudgetHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    budgets: list[BudgetSchema]
    total_count: int
