from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.domain.transaction_intelligence.enums import (
    CounterpartyType,
    FinancialClassification,
    TransactionDirection,
    TransactionStatus,
    TrendType,
)


def is_included_status(status: TransactionStatus) -> bool:
    """Return True if transaction status represents completed/settled historical actuals."""
    return status in {TransactionStatus.COMPLETED, TransactionStatus.SETTLED}


def map_status(raw_status: str) -> TransactionStatus:
    cleaned = str(raw_status or "").strip().upper()
    status_map = {
        "COMPLETED": TransactionStatus.COMPLETED,
        "SETTLED": TransactionStatus.SETTLED,
        "PENDING": TransactionStatus.PENDING,
        "FAILED": TransactionStatus.FAILED,
        "REVERSED": TransactionStatus.REVERSED,
        "CANCELLED": TransactionStatus.CANCELLED,
    }
    return status_map.get(cleaned, TransactionStatus.UNKNOWN)


def determine_direction(raw_direction: str, amount: Decimal) -> TransactionDirection:
    """
    Determine transaction direction relative to the user's account.

    Direction answers: Which way did money move?
    It does NOT determine financial classification (income vs expense vs transfer).
    """
    cleaned = str(raw_direction or "").strip().upper()
    if cleaned in {"INBOUND", "CREDIT", "DEPOSIT", "IN"}:
        return TransactionDirection.INBOUND
    if cleaned in {"OUTBOUND", "DEBIT", "WITHDRAWAL", "OUT", "DEBITED"}:
        return TransactionDirection.OUTBOUND
    return (
        TransactionDirection.INBOUND if amount > Decimal("0.00") else TransactionDirection.OUTBOUND
    )


def determine_classification(
    raw_classification: str,
    direction: TransactionDirection,
    raw: dict[str, Any],
) -> FinancialClassification:
    """
    Determine financial classification (INCOME, EXPENSE, TRANSFER, OTHER, UNKNOWN).

    Key Invariants:
    1. INBOUND does NOT automatically mean INCOME.
    2. OUTBOUND does NOT automatically mean EXPENSE.
    3. TRANSFERS must not distort income/expense analysis.
    """
    cleaned = str(raw_classification or "").strip().upper()
    if cleaned in {"INCOME", "SALARY", "PAYROLL"}:
        return FinancialClassification.INCOME
    if cleaned in {"EXPENSE", "PURCHASE", "PAYMENT"}:
        return FinancialClassification.EXPENSE
    if cleaned in {"TRANSFER", "INTERNAL_TRANSFER"}:
        return FinancialClassification.TRANSFER
    if cleaned in {"OTHER", "REFUND", "REVERSAL"}:
        return FinancialClassification.OTHER

    description = str(raw.get("description") or "").lower()
    if "refund" in description or "reversal" in description or "returned" in description:
        return FinancialClassification.OTHER

    transaction_type = str(raw.get("transaction_type") or "").strip().upper()
    if transaction_type in {"TRANSFER", "INTERNAL_TRANSFER"}:
        return FinancialClassification.TRANSFER

    source_type = str(raw.get("source_type") or "").strip().lower()
    if source_type in {"employer", "salary", "payroll"}:
        return FinancialClassification.INCOME
    if source_type in {"self", "own_account", "internal"}:
        return FinancialClassification.TRANSFER

    counterparty_type_str = str(raw.get("counterparty_type") or "").upper()
    if counterparty_type_str in {"EMPLOYER", "PAYROLL"}:
        return FinancialClassification.INCOME
    if counterparty_type_str == "SELF":
        return FinancialClassification.TRANSFER
    if counterparty_type_str == "BENEFICIARY":
        return FinancialClassification.TRANSFER

    if (
        "salary" in description or "payroll" in description
    ) and direction == TransactionDirection.INBOUND:
        return FinancialClassification.INCOME

    if "transfer" in description:
        return FinancialClassification.TRANSFER

    if direction == TransactionDirection.OUTBOUND and (
        raw.get("merchant") or raw.get("merchant_name")
    ):
        return FinancialClassification.EXPENSE

    if direction == TransactionDirection.OUTBOUND and (
        raw.get("beneficiary") or raw.get("beneficiary_name")
    ):
        return FinancialClassification.TRANSFER

    return FinancialClassification.UNKNOWN


def resolve_counterparty_type(
    raw: dict[str, Any],
    direction: TransactionDirection,
    classification: FinancialClassification,
) -> CounterpartyType:
    """
    Resolve counterparty relationship type.

    CounterpartyType represents relationship classification, NOT a separate database entity.
    SELF, EMPLOYER, and OTHER do not require separate domain model entities.
    """
    explicit = str(raw.get("counterparty_type") or raw.get("source_type") or "").strip().upper()
    if explicit in {"MERCHANT", "BUSINESS"}:
        return CounterpartyType.MERCHANT
    if explicit in {"BENEFICIARY", "RECIPIENT"}:
        return CounterpartyType.BENEFICIARY
    if explicit in {"EMPLOYER", "PAYROLL"}:
        return CounterpartyType.EMPLOYER
    if explicit in {"SELF", "OWN_ACCOUNT"}:
        return CounterpartyType.SELF
    if explicit in {"OTHER", "UNSPECIFIED"}:
        return CounterpartyType.OTHER

    tx_type = str(raw.get("transaction_type") or "").lower()
    if tx_type in {"internal_transfer", "self_transfer"}:
        return CounterpartyType.SELF

    source_type = str(raw.get("source_type") or "").lower()
    if source_type == "employer":
        return CounterpartyType.EMPLOYER
    if source_type == "self":
        return CounterpartyType.SELF

    if raw.get("merchant") or raw.get("merchant_name"):
        return CounterpartyType.MERCHANT
    if raw.get("beneficiary") or raw.get("beneficiary_name"):
        return CounterpartyType.BENEFICIARY

    if classification == FinancialClassification.TRANSFER:
        if direction == TransactionDirection.INBOUND or source_type == "self":
            return CounterpartyType.SELF
        return CounterpartyType.BENEFICIARY

    if classification == FinancialClassification.INCOME:
        if explicit == "EMPLOYER" or source_type in {"employer", "payroll"}:
            return CounterpartyType.EMPLOYER
        return CounterpartyType.OTHER

    if classification == FinancialClassification.EXPENSE:
        if raw.get("merchant") or raw.get("merchant_name"):
            return CounterpartyType.MERCHANT
        return CounterpartyType.OTHER

    return CounterpartyType.OTHER


def infer_category(raw: dict[str, Any], classification: FinancialClassification) -> str:
    """Deterministically infer transaction category from metadata without LLM calls."""
    cat = str(raw.get("category") or "").strip().upper()
    if cat and cat != "UNKNOWN":
        return cat

    if classification == FinancialClassification.INCOME:
        return "INCOME"
    if classification == FinancialClassification.TRANSFER:
        return "TRANSFER"

    desc = str(raw.get("description") or "").lower()
    merchant = str(raw.get("merchant_name") or raw.get("merchant") or "").lower()
    text = f"{desc} {merchant}".strip()

    if any(
        k in text for k in ["netflix", "spotify", "prime video", "dstv", "showmax", "app store"]
    ):
        return "SUBSCRIPTIONS"
    if any(k in text for k in ["uber", "bolt", "indrive", "airline", "flight", "taxi"]):
        return "TRANSPORT"
    if any(k in text for k in ["rent", "landlord", "lease payment"]):
        return "HOUSING"
    if any(k in text for k in ["electricity", "nepa", "phcn", "water bill"]):
        return "UTILITIES"
    if any(k in text for k in ["clinic", "hospital", "pharmacy", "medical"]):
        return "HEALTHCARE"
    if any(k in text for k in ["school fees", "tuition", "university fees"]):
        return "EDUCATION"
    if any(k in text for k in ["cinema", "filmhouse", "movie theater"]):
        return "ENTERTAINMENT"
    if any(k in text for k in ["supermarket", "restaurant", "eatery", "buka", "groceries"]):
        return "FOOD"
    if any(k in text for k in ["utility bill", "cable tv"]):
        return "BILLS"
    if any(k in text for k in ["piggyvest", "cowrywise", "savings deposit"]):
        return "SAVINGS"

    return "UNKNOWN"


def classify_trend(values: list[int | float | Decimal]) -> TrendType:
    """
    Pure deterministic trend classification function.

    Returns: INCREASING, DECREASING, STABLE, VARIABLE, INSUFFICIENT_DATA
    """
    numeric_vals = [Decimal(str(v)) for v in values if v is not None]
    if len(numeric_vals) < 2:
        return TrendType.INSUFFICIENT_DATA

    # Check if all values are identical
    if len(set(numeric_vals)) == 1:
        return TrendType.STABLE

    # Compute mean & coefficient of variation (CoV)
    mean = sum(numeric_vals, Decimal("0.00")) / Decimal(len(numeric_vals))
    if mean == Decimal("0.00"):
        return TrendType.STABLE

    variance = sum([(x - mean) ** 2 for x in numeric_vals], Decimal("0.00")) / Decimal(
        len(numeric_vals)
    )
    stddev = variance.sqrt()
    cov = float((stddev / mean) * Decimal(100))

    # Monotonic checks
    is_strictly_increasing = all(
        numeric_vals[i] < numeric_vals[i + 1] for i in range(len(numeric_vals) - 1)
    )
    is_strictly_decreasing = all(
        numeric_vals[i] > numeric_vals[i + 1] for i in range(len(numeric_vals) - 1)
    )

    # Calculate overall delta (first vs last)
    first_val = numeric_vals[0]
    last_val = numeric_vals[-1]
    total_change_pct = (
        float(((last_val - first_val) / max(first_val, Decimal("1.00"))) * Decimal(100))
        if first_val > 0
        else (100.0 if last_val > first_val else -100.0)
    )

    if is_strictly_increasing or total_change_pct >= 15.0:
        return TrendType.INCREASING
    if is_strictly_decreasing or total_change_pct <= -15.0:
        return TrendType.DECREASING
    if cov > 30.0:
        return TrendType.VARIABLE
    return TrendType.STABLE
