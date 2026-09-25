from __future__ import annotations

from dataclasses import dataclass

from app.core.amount_parser import AmountParse, parse_amount
from app.domain.confirmation.errors import InvalidAmountError


@dataclass(frozen=True)
class AmountValidationResult:
    """Result of validating a monetary amount."""

    valid: bool
    amount: int | None = None
    currency: str = "NGN"
    is_explicit: bool = False
    ambiguous_bare: int | None = None
    unresolved: bool = False
    note: str | None = None
    error: str | None = None


DEFAULT_MAX_TRANSACTION_LIMIT = 5_000_000  # ₦5,000,000


class AmountValidator:
    """
    Dedicated monetary amount validation component.

    Detects explicit monetary amounts, normalizes slang, enforces positive values and configured limits.
    """

    def __init__(self, max_transaction_limit: int = DEFAULT_MAX_TRANSACTION_LIMIT) -> None:
        self.max_transaction_limit = max_transaction_limit

    def validate(
        self,
        text: str,
        *,
        current_amount: int | None = None,
    ) -> AmountValidationResult:
        """
        Validate and normalize a user input string for monetary amounts.
        """
        parsed: AmountParse = parse_amount(text)

        if parsed.unresolved:
            return AmountValidationResult(
                valid=False,
                unresolved=True,
                error="I couldn't read that amount clearly. Please write it in figures, e.g. 10k or ₦10,000.",
            )

        if parsed.ambiguous is not None:
            # Check context inferencing
            if (
                current_amount is not None
                and current_amount >= 1_000
                and current_amount % 1_000 == 0
            ):
                inferred = parsed.ambiguous * 1_000
                if inferred > self.max_transaction_limit:
                    return AmountValidationResult(
                        valid=False,
                        error=f"Amount exceeds maximum transfer limit of ₦{self.max_transaction_limit:,}.",
                    )
                return AmountValidationResult(
                    valid=True,
                    amount=inferred,
                    currency="NGN",
                    is_explicit=True,
                    note=f"Inferred ₦{inferred:,} from bare figure '{parsed.ambiguous}' based on context.",
                )

            return AmountValidationResult(
                valid=False,
                ambiguous_bare=parsed.ambiguous,
                error=f"Bare figure '{parsed.ambiguous}' is ambiguous.",
            )

        if parsed.amount is not None:
            if parsed.amount <= 0:
                raise InvalidAmountError("Transfer amount must be greater than zero.")

            if parsed.amount > self.max_transaction_limit:
                return AmountValidationResult(
                    valid=False,
                    error=f"Amount ₦{parsed.amount:,} exceeds maximum transaction limit of ₦{self.max_transaction_limit:,}.",
                )

            return AmountValidationResult(
                valid=True,
                amount=parsed.amount,
                currency="NGN",
                is_explicit=True,
                note=parsed.note,
            )

        return AmountValidationResult(valid=False)
