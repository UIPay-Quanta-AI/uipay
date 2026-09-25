from __future__ import annotations

import re
from dataclasses import dataclass

from app.clients.ui_pay.base import UIPayClient
from app.core.context import RequestContext
from app.domain.confirmation.errors import AccountValidationError


@dataclass(frozen=True)
class AccountValidationResult:
    """Provider-neutral account validation result."""

    valid: bool
    account_name: str | None = None
    bank_code: str | None = None
    bank_name: str | None = None
    account_number: str | None = None
    provider_reference: str | None = None
    error: str | None = None


class AccountValidator:
    """
    Dedicated account validation component.

    The LLM must NEVER invent or infer the account holder's name.
    The authoritative account name originates strictly from UI Pay backend validation.
    """

    def __init__(self, client: UIPayClient) -> None:
        self._client = client

    @staticmethod
    def normalize_account_number(account_number: str) -> str:
        """Strip spaces, hyphens, and non-digit characters."""
        return re.sub(r"\D", "", account_number.strip())

    async def validate(
        self,
        *,
        bank_code: str,
        account_number: str,
        context: RequestContext,
    ) -> AccountValidationResult:
        """
        Validate destination account information against the UI Pay backend.
        """
        normalized_account = self.normalize_account_number(account_number)

        if not normalized_account:
            return AccountValidationResult(valid=False, error="Account number cannot be empty.")

        if len(normalized_account) != 10:
            return AccountValidationResult(
                valid=False,
                error=f"Account number must be 10 digits (got {len(normalized_account)}).",
            )

        try:
            # Query backend search/validation
            beneficiaries = await self._client.search_beneficiaries(
                user_id=context.user_id,
                query=normalized_account,
            )

            if beneficiaries:
                record = beneficiaries[0]
                return AccountValidationResult(
                    valid=True,
                    account_name=record["account_name"],
                    bank_code=bank_code,
                    bank_name=record.get("bank_name", bank_code),
                    account_number=normalized_account,
                    provider_reference=f"acct-val-{record['id']}",
                )

            return AccountValidationResult(
                valid=False,
                error="Account number could not be verified by UI Pay.",
            )
        except Exception as exc:
            raise AccountValidationError("UI Pay backend account validation failed.") from exc
