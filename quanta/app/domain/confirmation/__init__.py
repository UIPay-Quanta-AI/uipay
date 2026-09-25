"""
Confirmation domain module exports.
"""

from app.domain.confirmation.errors import (
    ConfirmationAlreadyConsumedError,
    ConfirmationError,
    ConfirmationExpiredError,
    ConfirmationNotFoundError,
    ConfirmationOwnershipError,
    InvalidConfirmationStateError,
)
from app.domain.confirmation.manager import ConfirmationManager
from app.domain.confirmation.models import Confirmation, ConfirmationStatus
from app.domain.confirmation.resolver import ConfirmationIntent, ConfirmationResolver
from app.domain.confirmation.store import ConfirmationStore, InMemoryConfirmationStore

__all__ = [
    "Confirmation",
    "ConfirmationAlreadyConsumedError",
    "ConfirmationError",
    "ConfirmationExpiredError",
    "ConfirmationIntent",
    "ConfirmationManager",
    "ConfirmationNotFoundError",
    "ConfirmationOwnershipError",
    "ConfirmationResolver",
    "ConfirmationStatus",
    "ConfirmationStore",
    "InMemoryConfirmationStore",
    "InvalidConfirmationStateError",
]
