from __future__ import annotations

from pydantic import BaseModel, Field


class TransferPreparation(BaseModel):
    """
    Trusted output of the prepare_transfer tool.

    All fields originate from the controlled tool result, not from LLM
    natural-language output.  Currency is always NGN – it is set by the
    application, never inferred from the user's wording or the model's
    response.
    """

    reference: str = Field(min_length=1)
    beneficiary_id: str = Field(min_length=1)
    amount: int = Field(gt=0)
    currency: str = Field(default="NGN", pattern=r"^[A-Z]{3}$")


class PreparedTransfer(BaseModel):
    """
    Enriched transfer summary shown to the user before they confirm.

    Populated from the trusted tool result *and* the authoritative UI Pay
    beneficiary record – never from the LLM's natural-language response.
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
