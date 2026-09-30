from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BudgetStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class UpdateReason(str, Enum):
    INITIAL_GENERATION = "initial_generation"
    INCOME_CHANGE = "income_change"
    EXPENSE_CHANGE = "expense_change"
    GOAL_CHANGE = "goal_change"
    USER_REBALANCE = "user_rebalance"
    FINANCIAL_CHANGE = "financial_change"
    OTHER = "other"


class BudgetDomainError(Exception):
    """Domain validation error for budgets."""


class BudgetAllocation(BaseModel):
    """Allocation of budget toward a spending or savings category."""

    model_config = ConfigDict(frozen=True)

    category: str = Field(min_length=1)
    allocated_amount: Decimal = Field(ge=Decimal("0.00"))
    notes: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if not v or not v.strip():
            raise BudgetDomainError("Allocation category cannot be empty")
        return v.strip().lower()


class GoalAllocation(BaseModel):
    """Allocation of budget toward a specific financial goal."""

    model_config = ConfigDict(frozen=True)

    goal_id: str = Field(min_length=1)
    goal_name: str = Field(min_length=1)
    allocated_amount: Decimal = Field(ge=Decimal("0.00"))


class IncomePlan(BaseModel):
    """Planned income details for the budget period."""

    model_config = ConfigDict(frozen=True)

    expected_income: Decimal = Field(ge=Decimal("0.00"))
    income_sources: list[str] = Field(default_factory=list)


class TransactionBudgetContext(BaseModel):
    """
    Sanitized observational context derived from historical transaction activity.
    This context is optional supporting evidence; Financial Profile and Goals remain authoritative.
    """

    model_config = ConfigDict(frozen=True)

    data_available: bool = False
    lookback_period: dict[str, str] | None = None
    historical_periods: list[dict[str, Any]] = Field(default_factory=list)
    trends: dict[str, Any] = Field(default_factory=dict)
    category_trends: dict[str, Any] = Field(default_factory=dict)
    notable_changes: list[str] = Field(default_factory=list)


class Budget(BaseModel):
    """
    Authoritative domain model for a user's budget.

    A budget is defined by explicit start_date and end_date. It is NOT inherently calendar monthly.
    Updates to a budget do NOT restart the period; they create a new version for the SAME start_date and end_date.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    start_date: date
    end_date: date
    currency: str = Field(default="NGN")
    version: int = Field(default=1, ge=1)
    status: BudgetStatus = Field(default=BudgetStatus.ACTIVE)
    income_plan: IncomePlan
    allocations: list[BudgetAllocation] = Field(default_factory=list)
    goal_allocations: list[GoalAllocation] = Field(default_factory=list)
    previous_version_id: str | None = None
    update_reason: UpdateReason = Field(default=UpdateReason.INITIAL_GENERATION)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise BudgetDomainError("user_id cannot be empty")
        return v.strip()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v != "NGN":
            raise BudgetDomainError(f"Unsupported budget currency: {v}. Only NGN is supported.")
        return v

    @model_validator(mode="after")
    def validate_dates_and_totals(self) -> Budget:
        if self.start_date >= self.end_date:
            raise BudgetDomainError(
                f"Budget start_date ({self.start_date}) must be strictly before end_date ({self.end_date})."
            )

        total_allocations = sum((a.allocated_amount for a in self.allocations), Decimal("0.00"))
        total_goal_allocations = sum(
            (g.allocated_amount for g in self.goal_allocations), Decimal("0.00")
        )
        total_planned = total_allocations + total_goal_allocations

        if total_planned > self.income_plan.expected_income:
            raise BudgetDomainError(
                f"Total budget allocations ({total_planned}) cannot exceed expected income ({self.income_plan.expected_income})."
            )

        return self

    @property
    def total_allocated_expenses(self) -> Decimal:
        return sum((a.allocated_amount for a in self.allocations), Decimal("0.00"))

    @property
    def total_allocated_goals(self) -> Decimal:
        return sum((g.allocated_amount for g in self.goal_allocations), Decimal("0.00"))

    @property
    def total_unallocated_income(self) -> Decimal:
        return max(
            Decimal("0.00"),
            self.income_plan.expected_income
            - (self.total_allocated_expenses + self.total_allocated_goals),
        )

    def validate_ownership(self, expected_user_id: str) -> None:
        """Verify that the budget belongs to the specified user."""
        if self.user_id != expected_user_id:
            raise BudgetDomainError(
                f"Budget ownership mismatch. Expected user '{expected_user_id}', got '{self.user_id}'."
            )

    def remaining_period(self, as_of_date: date) -> tuple[date, date]:
        """
        Calculate the remaining portion of the original budget period as of a given date.
        Does NOT alter or restart the budget period boundaries.
        """
        effective_start = max(as_of_date, self.start_date)
        if effective_start > self.end_date:
            raise BudgetDomainError(
                f"Cannot calculate remaining period for date ({as_of_date}) past budget end_date ({self.end_date})."
            )
        return effective_start, self.end_date
