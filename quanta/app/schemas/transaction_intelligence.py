from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TransactionIntelligenceRequest(BaseModel):
    """
    Application request schema for transaction intelligence analysis.
    Note: user_id is NOT included in request body; identity is derived from RequestContext.
    """

    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date


class SanitizedTransactionContext(BaseModel):
    """
    LLM-facing sanitized context. Contains aggregated financial observations,
    trends, recurring patterns, and budget review signals.
    Operational references and raw transaction lists are excluded.
    """

    model_config = ConfigDict(frozen=True)

    data_available: bool = False
    lookback_period: dict[str, str] | None = None
    historical_periods: list[dict[str, Any]] = Field(default_factory=list)
    trends: dict[str, Any] = Field(default_factory=dict)
    notable_changes: list[str] = Field(default_factory=list)
    budget_review_signals: list[dict[str, Any]] = Field(default_factory=list)


class TransactionIntelligenceResponse(BaseModel):
    """Response schema wrapping transaction intelligence results."""

    model_config = ConfigDict(frozen=True)

    success: bool = True
    data_available: bool = False
    lookback_period: dict[str, str] | None = None
    trends: dict[str, Any] = Field(default_factory=dict)
    notable_changes: list[str] = Field(default_factory=list)
    budget_review_signals: list[dict[str, Any]] = Field(default_factory=list)
    income_totals: dict[str, Any] = Field(default_factory=dict)
    expense_totals: dict[str, Any] = Field(default_factory=dict)
    sanitized_context: SanitizedTransactionContext
