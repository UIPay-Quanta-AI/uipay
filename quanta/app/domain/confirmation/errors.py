from __future__ import annotations


class ConfirmationError(Exception):
    """Base exception for confirmation domain failures."""


class ConfirmationNotFoundError(ConfirmationError):
    """Raised when a confirmation record cannot be found."""


class ConfirmationExpiredError(ConfirmationError):
    """Raised when an operation attempts to confirm an expired record."""


class ConfirmationAlreadyConsumedError(ConfirmationError):
    """Raised when an operation attempts to reuse a consumed confirmation (replay prevention)."""


class ConfirmationOwnershipError(ConfirmationError):
    """Raised when a user or session attempts to confirm a record owned by another identity."""


class InvalidConfirmationStateError(ConfirmationError):
    """Raised when an invalid confirmation state transition is requested."""


class TransferGuardError(ConfirmationError):
    """Raised when transfer guard policies fail closed."""


class AccountValidationError(ConfirmationError):
    """Raised when account structural or backend validation fails."""


class InvalidAmountError(ConfirmationError):
    """Raised when an amount is negative, zero, or violates limit policies."""
