from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.financial_profile.models import EmploymentType, IncomeFrequency


class FinancialProfileSchema(BaseModel):
    """Boundary schema for financial profile representation."""

    model_config = ConfigDict(frozen=True)

    monthly_income: Decimal = Field(ge=Decimal("0.00"))
    income_frequency: IncomeFrequency
    employment_type: EmploymentType
    fixed_expenses: Decimal = Field(ge=Decimal("0.00"))
    variable_expenses: Decimal = Field(ge=Decimal("0.00"))
    savings_target: Decimal = Field(ge=Decimal("0.00"))
    currency: str = Field(default="NGN")
    created_at: datetime
    updated_at: datetime


class GetFinancialProfileResponse(BaseModel):
    """Response boundary schema when retrieving a financial profile."""

    model_config = ConfigDict(frozen=True)

    profile: FinancialProfileSchema


class UpdateFinancialProfileRequest(BaseModel):
    """Request boundary schema for updating a financial profile."""

    model_config = ConfigDict(frozen=True)

    monthly_income: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    income_frequency: IncomeFrequency | None = None
    employment_type: EmploymentType | None = None
    fixed_expenses: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    variable_expenses: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    savings_target: Decimal | None = Field(default=None, ge=Decimal("0.00"))


class UpdateFinancialProfileResponse(BaseModel):
    """Response boundary schema after updating a financial profile."""

    model_config = ConfigDict(frozen=True)

    profile: FinancialProfileSchema
    updated_fields: list[str]
