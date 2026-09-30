from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.transaction_intelligence.enums import (
    CounterpartyType,
    DataQualityCode,
    FinancialClassification,
    TransactionDirection,
    TransactionStatus,
    TrendType,
)


class FinancialObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    period: str | None = None
    value: Decimal | None = None
    comparison: Decimal | None = None
    change_amount: Decimal | None = None
    change_percentage: Decimal | None = None
    significant: bool = False
    evidence: list[str] = Field(default_factory=list)


class BudgetReviewSignal(BaseModel):
    model_config = ConfigDict(frozen=True)

    detected: bool = True
    reason: str = Field(min_length=1)
    affected_area: str = "budget_review"
    observation: str
    evidence: list[str] = Field(default_factory=list)
    change_percentage: Decimal | None = None
    current_value: Decimal | None = None
    historical_baseline: Decimal | None = None


class NormalizedTransaction(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    reference: str | None = None
    amount: Decimal = Field(ge=Decimal("0.00"))
    currency: str = Field(default="NGN")
    direction: TransactionDirection
    classification: FinancialClassification = FinancialClassification.UNKNOWN
    category: str = Field(default="UNKNOWN")
    counterparty_type: CounterpartyType = CounterpartyType.UNKNOWN
    counterparty_name: str | None = None
    merchant: dict[str, Any] | None = None
    beneficiary: dict[str, Any] | None = None
    status: TransactionStatus = TransactionStatus.UNKNOWN
    description: str | None = None
    date: date
    # Raw provider payload is stored but excluded from serialization to avoid accidental leaks.
    source_data: dict[str, Any] = Field(default_factory=dict, exclude=True)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        if value != "NGN":
            raise ValueError("Only NGN transactions are supported in Quanta.")
        return value

    def sanitize_for_llm(self) -> dict[str, Any]:
        """
        Return sanitized representation suitable for LLM context.
        Operational ID, reference and source payload are strictly excluded.
        """
        return {
            "amount": float(self.amount),
            "currency": self.currency,
            "direction": self.direction.value,
            "classification": self.classification.value,
            "category": self.category,
            "counterparty_type": self.counterparty_type.value,
            "counterparty_name": self.counterparty_name,
            "status": self.status.value,
            "description": self.description,
            "date": self.date.isoformat(),
        }


class TransactionIntelligenceResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_available: bool = False
    lookback_period: dict[str, str] | None = None
    normalized_transactions: list[NormalizedTransaction] = Field(default_factory=list)
    historical_periods: list[dict[str, Any]] = Field(default_factory=list)
    trends: dict[str, Any] = Field(default_factory=dict)
    notable_changes: list[str] = Field(default_factory=list)
    financial_observations: list[FinancialObservation] = Field(default_factory=list)
    budget_review_signals: list[dict[str, Any]] = Field(default_factory=list)
    income_totals: dict[str, Any] = Field(default_factory=dict)
    expense_totals: dict[str, Any] = Field(default_factory=dict)
    transaction_budget_context: Any = None
    invalid_transactions_count: int = 0
    data_quality: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime | None = None


__all__ = [
    "BudgetReviewSignal",
    "CounterpartyType",
    "DataQualityCode",
    "FinancialClassification",
    "FinancialObservation",
    "NormalizedTransaction",
    "TransactionDirection",
    "TransactionIntelligenceResult",
    "TransactionStatus",
    "TrendType",
]
