from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ConfirmationStatus(str, Enum):
    """Lifecycle statuses for pending transfer confirmations."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    CONSUMED = "consumed"
    INVALID = "invalid"


@dataclass
class Confirmation:
    """
    Authoritative state for a prepared financial operation awaiting confirmation.

    Sensitive authentication credentials (PINs, passwords, API keys) must NEVER be stored here.
    """

    confirmation_id: str
    request_id: str
    user_id: str
    session_id: str
    operation: str
    amount: int
    currency: str
    prepared_reference: str
    created_at: datetime
    expires_at: datetime
    beneficiary_id: str | None = None
    account_number: str | None = None
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.fingerprint:
            self.fingerprint = self.compute_fingerprint()

    def compute_fingerprint(self) -> str:
        """
        Generate a deterministic integrity fingerprint for the prepared operation.
        """
        raw = (
            f"{self.user_id}|{self.session_id}|{self.operation}|"
            f"{self.beneficiary_id or ''}|{self.account_number or ''}|"
            f"{self.amount}|{self.currency}|{self.prepared_reference}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def is_valid_fingerprint(self) -> bool:
        """
        Verify that the record payload matches its integrity fingerprint.
        """
        return self.fingerprint == self.compute_fingerprint()
