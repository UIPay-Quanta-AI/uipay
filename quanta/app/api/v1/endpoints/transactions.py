"""
Transaction Intelligence API endpoints.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.core.context import RequestContext
from app.dependencies.services import get_transaction_intelligence_service
from app.domain.transaction_intelligence.models import TransactionIntelligenceResult
from app.services.transaction_intelligence_service import TransactionIntelligenceService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/intelligence", response_model=TransactionIntelligenceResult)
async def get_transaction_intelligence(
    start_date: date = Query(...),
    end_date: date = Query(...),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    x_locale: str | None = Header(default=None, alias="X-Locale"),
    ti_service: TransactionIntelligenceService = Depends(get_transaction_intelligence_service),
) -> TransactionIntelligenceResult:
    """
    Retrieve transaction intelligence insights for specified date window.
    User identity comes authoritatively from X-User-ID header.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-ID header.",
        )

    if not x_session_id or not x_session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-Session-ID header.",
        )

    context = RequestContext.create(
        user_id=x_user_id,
        session_id=x_session_id,
        operation="TRANSACTION_INTELLIGENCE",
        locale=x_locale,
    )

    try:
        return await ti_service.analyze(
            context=context,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
