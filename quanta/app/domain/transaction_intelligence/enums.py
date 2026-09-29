from __future__ import annotations

from enum import Enum


class TransactionDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class FinancialClassification(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class TransactionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    SETTLED = "SETTLED"
    PENDING = "PENDING"
    FAILED = "FAILED"
    REVERSED = "REVERSED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class CounterpartyType(str, Enum):
    MERCHANT = "MERCHANT"
    BENEFICIARY = "BENEFICIARY"
    EMPLOYER = "EMPLOYER"
    SELF = "SELF"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class TrendType(str, Enum):
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    VARIABLE = "VARIABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DataQualityCode(str, Enum):
    OK = "OK"
    NO_DATA = "NO_DATA"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    INVALID_DATA_PRESENT = "INVALID_DATA_PRESENT"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
