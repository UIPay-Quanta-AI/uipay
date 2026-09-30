"""
Financial Goals API endpoints.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies.services import get_goal_service
from app.domain.goals.models import FinancialGoal, GoalStatus
from app.services.goal_service import GoalService

router = APIRouter(prefix="/goals", tags=["goals"])


class CreateGoalRequest(BaseModel):
    name: str = Field(..., min_length=1)
    target_amount: Decimal = Field(..., gt=Decimal("0.00"))
    target_date: date | None = None


class UpdateGoalRequest(BaseModel):
    updates: dict[str, Any]


@router.get("", response_model=list[FinancialGoal])
async def get_goals(
    status_filter: GoalStatus | None = None,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    goal_service: GoalService = Depends(get_goal_service),
) -> list[FinancialGoal]:
    """
    Retrieve goals for authenticated user context.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-ID header.",
        )

    try:
        return await goal_service.get_goals(
            user_id=x_user_id.strip(),
            status=status_filter,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("", response_model=FinancialGoal)
async def create_goal(
    body: CreateGoalRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    goal_service: GoalService = Depends(get_goal_service),
) -> FinancialGoal:
    """
    Create a new goal for authenticated user context.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-ID header.",
        )

    try:
        return await goal_service.create_goal(
            user_id=x_user_id.strip(),
            name=body.name,
            target_amount=body.target_amount,
            target_date=body.target_date,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put("/{goal_id}", response_model=FinancialGoal)
async def update_goal(
    goal_id: str,
    body: UpdateGoalRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    goal_service: GoalService = Depends(get_goal_service),
) -> FinancialGoal:
    """
    Update a goal's progress or status for authenticated user context.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-ID header.",
        )

    try:
        return await goal_service.update_goal(
            user_id=x_user_id.strip(),
            goal_identifier=goal_id,
            updates=body.updates,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
