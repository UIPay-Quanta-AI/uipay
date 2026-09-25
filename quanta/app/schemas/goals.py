from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.goals.models import GoalStatus


class GoalSchema(BaseModel):
    """Boundary representation of a financial goal."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    target_amount: Decimal = Field(gt=Decimal("0.00"))
    current_amount: Decimal = Field(ge=Decimal("0.00"))
    remaining_amount: Decimal = Field(ge=Decimal("0.00"))
    target_date: date | None = None
    currency: str = Field(default="NGN")
    status: GoalStatus
    created_at: datetime
    updated_at: datetime


class CreateGoalRequest(BaseModel):
    """Request schema for creating a financial goal."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    target_amount: Decimal = Field(gt=Decimal("0.00"))
    target_date: date | None = None


class UpdateGoalRequest(BaseModel):
    """Request schema for updating a financial goal."""

    model_config = ConfigDict(frozen=True)

    goal_id: str = Field(min_length=1)
    name: str | None = Field(default=None, min_length=1)
    target_amount: Decimal | None = Field(default=None, gt=Decimal("0.00"))
    current_amount: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    target_date: date | None = None
    status: GoalStatus | None = None


class GoalResponse(BaseModel):
    """Response schema for a single financial goal."""

    model_config = ConfigDict(frozen=True)

    goal: GoalSchema


class GoalListResponse(BaseModel):
    """Response schema for a list of financial goals."""

    model_config = ConfigDict(frozen=True)

    goals: list[GoalSchema]
    total_count: int
