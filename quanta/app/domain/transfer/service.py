from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.clients.ui_pay.base import UIPayClient
from app.core.context import RequestContext
from app.domain.transfer.account import AccountValidator
from app.domain.transfer.amount import AmountValidator
from app.domain.transfer.context import TransferContext
from app.domain.transfer.guard import TransferGuard


@dataclass
class PreparedTransferDomainResult:
    """Domain output of preparing a transfer."""

    success: bool
    reference: str | None = None
    beneficiary_id: str | None = None
    recipient_name: str | None = None
    bank_name: str | None = None
    account_number: str | None = None
    amount: int | None = None
    currency: str = "NGN"
    clarification: str | None = None
    error: str | None = None


class TransferDomainService:
    """
    Coordinates account validation, amount validation, transfer guards, and preparation.

    Follows the principle: LLM Proposes. Quanta Validates and Governs. UI Pay Authorizes and Executes.
    """

    def __init__(
        self,
        client: UIPayClient,
        amount_validator: AmountValidator | None = None,
    ) -> None:
        self._client = client
        self._account_validator = AccountValidator(client)
        self._amount_validator = amount_validator or AmountValidator()

    async def process_user_turn(
        self,
        *,
        text: str,
        context: RequestContext,
        transfer_context: TransferContext,
        beneficiaries_list: list[dict[str, Any]] | None = None,
    ) -> TransferContext:
        """
        Update the authoritative TransferContext from the latest user input.
        """
        transfer_context.update_from_user_input(
            text,
            beneficiaries_list=beneficiaries_list,
        )

        return transfer_context

    def validate_guard(
        self,
        *,
        context: RequestContext,
        transfer_context: TransferContext,
    ) -> None:
        """
        Validate transfer readiness using TransferGuard.
        Raises TransferGuardError if context is incomplete.
        """
        guard = TransferGuard(transfer_context)
        guard.validate_prepare_readiness(context)
