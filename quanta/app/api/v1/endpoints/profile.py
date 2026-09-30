"""
Financial Profile API endpoints for retrieving and batch updating profile information.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.dependencies.services import get_financial_profile_service
from app.domain.financial_profile.models import FinancialProfile
from app.services.financial_profile_service import FinancialProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdateRequest(BaseModel):
    updates: dict[str, Any]


@router.get("", response_model=FinancialProfile)
async def get_profile(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    profile_service: FinancialProfileService = Depends(get_financial_profile_service),
) -> FinancialProfile:
    """
    Retrieve financial profile for authenticated user context.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-ID header.",
        )

    try:
        return await profile_service.get_profile(user_id=x_user_id.strip())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("", response_model=FinancialProfile)
async def update_profile(
    body: ProfileUpdateRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    profile_service: FinancialProfileService = Depends(get_financial_profile_service),
) -> FinancialProfile:
    """
    Batch update financial profile for authenticated user context.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-ID header.",
        )

    try:
        updated_profile, _fields = await profile_service.update_profile(
            user_id=x_user_id.strip(),
            updates=body.updates,
        )
        return updated_profile
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
