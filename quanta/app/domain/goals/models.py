from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class GoalDomainError(Exception):
    """Domain rule or invariant violation for financial goals."""


class FinancialGoal(BaseModel):
    """
    Authoritative domain representation of a user's financial goal.
    Goals are planning and tracking objects, NOT payment instructions.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    target_amount: Decimal = Field(gt=Decimal("0.00"))
    current_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    target_date: date | None = None
    currency: str = Field(default="NGN")
    status: GoalStatus = Field(default=GoalStatus.ACTIVE)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise GoalDomainError("user_id cannot be empty")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise GoalDomainError("Goal name cannot be empty")
        return v.strip()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v != "NGN":
            raise GoalDomainError(f"Unsupported goal currency: {v}. Only NGN is supported.")
        return v

    @model_validator(mode="after")
    def validate_amounts_and_status(self) -> FinancialGoal:
        if self.target_amount <= Decimal("0.00"):
            raise GoalDomainError("Target amount must be strictly greater than zero")

        if self.current_amount < Decimal("0.00"):
            raise GoalDomainError("Current amount cannot be negative")

        if self.current_amount > self.target_amount:
            raise GoalDomainError(
                f"Current amount ({self.current_amount}) cannot exceed target amount ({self.target_amount})"
            )

        return self

    @property
    def remaining_amount(self) -> Decimal:
        """Deterministic calculation of remaining amount to satisfy goal."""
        return max(Decimal("0.00"), self.target_amount - self.current_amount)

    def validate_ownership(self, expected_user_id: str) -> None:
        """Verify that the goal belongs to the specified user."""
        if self.user_id != expected_user_id:
            raise GoalDomainError(
                f"Goal ownership mismatch. Expected user '{expected_user_id}', got '{self.user_id}'."
            )

    def validate_update(
        self, new_current_amount: Decimal | None = None, new_status: GoalStatus | None = None
    ) -> None:
        """Enforce domain rules when attempting to modify a goal."""
        if self.status == GoalStatus.CANCELLED:
            raise GoalDomainError("Cancelled goals cannot be updated.")

        if (
            self.status == GoalStatus.COMPLETED
            and new_current_amount is not None
            and new_current_amount != self.target_amount
            and new_status != GoalStatus.ACTIVE
        ):
            raise GoalDomainError(
                "Completed goals cannot receive ordinary progress updates unless reactivated."
            )
