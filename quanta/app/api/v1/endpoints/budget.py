"""
Budget API endpoints for retrieving, generating, and viewing version history of budgets.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.dependencies.services import get_budget_service
from app.domain.budget.models import Budget
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/budget", tags=["budget"])


class GenerateBudgetRequest(BaseModel):
    start_date: date
    end_date: date
    income_override: Decimal | None = None
    custom_allocations: list[dict[str, Any]] | None = None


@router.get("", response_model=Budget | None)
async def get_current_budget(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    budget_service: BudgetService = Depends(get_budget_service),
) -> Budget | None:
    """
    Retrieve active budget for authenticated user context.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-ID header.",
        )

    try:
        return await budget_service.get_current_budget(user_id=x_user_id.strip())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("", response_model=Budget)
async def generate_budget(
    body: GenerateBudgetRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    budget_service: BudgetService = Depends(get_budget_service),
) -> Budget:
    """
    Generate a new budget for specified start and end dates.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-ID header.",
        )

    try:
        return await budget_service.generate_budget(
            user_id=x_user_id.strip(),
            start_date=body.start_date,
            end_date=body.end_date,
            income_override=body.income_override,
            custom_allocations=body.custom_allocations,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/history", response_model=list[Budget])
async def get_budget_history(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    budget_service: BudgetService = Depends(get_budget_service),
) -> list[Budget]:
    """
    Retrieve budget version history for authenticated user context.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-ID header.",
        )

    try:
        return await budget_service.get_budget_history(user_id=x_user_id.strip())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
