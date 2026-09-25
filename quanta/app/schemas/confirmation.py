from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.confirmation.resolver import (
    EXPLICIT_CANCEL_PHRASES as CANCELLATION_PHRASES,
)
from app.domain.confirmation.resolver import (
    EXPLICIT_CONFIRM_PHRASES as CONFIRMATION_PHRASES,
)
from app.domain.confirmation.resolver import (
    ConfirmationIntent,
    ConfirmationResolver,
)


@dataclass
class PendingConfirmation:
    """
    Authoritative state for a prepared transfer awaiting user confirmation.
    """

    reference: str
    beneficiary_id: str
    amount: int
    currency: str
    created_at: datetime
    expires_at: datetime


_resolver = ConfirmationResolver()


def _normalize_confirmation_input(text: str) -> str:
    """Normalize confirmation/cancellation text for deterministic matching."""
    return _resolver.normalize(text)


def is_confirmation(text: str) -> bool:
    """Return True only for explicitly allow-listed confirmation phrases."""
    return _resolver.resolve(text) == ConfirmationIntent.CONFIRM


def is_cancellation(text: str) -> bool:
    """Return True only for explicitly allow-listed cancellation phrases."""
    return _resolver.resolve(text) == ConfirmationIntent.CANCEL


def classify_confirmation_input(text: str) -> str | None:
    """Classify a pending-transfer response without invoking the LLM."""
    intent = _resolver.resolve(text)
    if intent == ConfirmationIntent.CONFIRM:
        return "confirm"
    if intent == ConfirmationIntent.CANCEL:
        return "cancel"
    return None


__all__ = [
    "CANCELLATION_PHRASES",
    "CONFIRMATION_PHRASES",
    "PendingConfirmation",
    "classify_confirmation_input",
    "is_cancellation",
    "is_confirmation",
]
