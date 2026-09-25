from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncomeFrequency(str, Enum):
    MONTHLY = "monthly"
    BIWEEKLY = "biweekly"
    WEEKLY = "weekly"
    IRREGULAR = "irregular"


class EmploymentType(str, Enum):
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    FREELANCE = "freelance"
    UNEMPLOYED = "unemployed"
    OTHER = "other"


class FinancialProfileDomainError(Exception):
    """Domain validation or rule violation for financial profiles."""


class FinancialProfile(BaseModel):
    """
    Authoritative domain representation of a user's financial profile.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str = Field(min_length=1)
    monthly_income: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    income_frequency: IncomeFrequency = Field(default=IncomeFrequency.MONTHLY)
    employment_type: EmploymentType = Field(default=EmploymentType.SALARIED)
    fixed_expenses: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    variable_expenses: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    savings_target: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    currency: str = Field(default="NGN")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise FinancialProfileDomainError("user_id cannot be empty")
        return v.strip()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v != "NGN":
            raise FinancialProfileDomainError(f"Unsupported currency: {v}. Only NGN is supported.")
        return v

    @field_validator("monthly_income", "fixed_expenses", "variable_expenses", "savings_target")
    @classmethod
    def validate_non_negative_amount(cls, v: Decimal) -> Decimal:
        if v < Decimal("0.00"):
            raise FinancialProfileDomainError("Monetary values cannot be negative")
        return v

    def validate_ownership(self, expected_user_id: str) -> None:
        """Verify that the profile belongs to the expected user context."""
        if self.user_id != expected_user_id:
            raise FinancialProfileDomainError(
                f"Profile ownership mismatch. Expected user_id '{expected_user_id}', got '{self.user_id}'."
            )
