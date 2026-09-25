from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class TransferPreparation(BaseModel):
    """
    Trusted output of the prepare_transfer tool.

    All fields originate from the controlled tool result, not from LLM natural-language output.
    Currency is always NGN.
    """

    reference: str = Field(min_length=1)
    beneficiary_id: str = Field(min_length=1)
    amount: int = Field(gt=0)
    currency: str = Field(default="NGN", pattern=r"^[A-Z]{3}$")


class PreparedTransfer(BaseModel):
    """
    Enriched transfer summary shown to the user before they confirm.

    Populated from trusted tool result and authoritative UI Pay backend record.
    """

    reference: str = Field(min_length=1)
    beneficiary_id: str = Field(min_length=1)
    recipient_name: str = Field(min_length=1)
    bank_name: str = Field(min_length=1)
    masked_account_number: str = Field(min_length=1)
    amount: int = Field(gt=0)
    currency: str = Field(default="NGN", pattern=r"^[A-Z]{3}$")

    @classmethod
    def mask_account(cls, account_number: str) -> str:
        """Return last-four-digit masked account number."""
        if len(account_number) <= 4:
            return account_number
        return "*" * (len(account_number) - 4) + account_number[-4:]


@dataclass
class TurnFacts:
    """What the *latest* user turn explicitly said (never carried over)."""

    explicit_beneficiary: str | None = None
    explicit_amount: int | None = None
    ambiguous_amount: int | None = None
    amount_unresolved: bool = False
    notes: list[str] = field(default_factory=list)
