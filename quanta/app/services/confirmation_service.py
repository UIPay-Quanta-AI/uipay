from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.clients.ui_pay.base import UIPayClient
from app.schemas.confirmation import PendingConfirmation, classify_confirmation_input
from app.schemas.response import QuantaResponse


@dataclass
class ConfirmationTurnResult:
    """Result of evaluating a confirmation turn."""

    handled: bool
    action: str | None = None
    response: QuantaResponse | None = None
    pending: PendingConfirmation | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)


async def handle_pending_confirmation(
    *,
    user_input: str,
    pending: PendingConfirmation,
    client: UIPayClient | None = None,
    beneficiaries_list: list[dict[str, Any]] | None = None,
) -> ConfirmationTurnResult:
    """Handle a pending confirmation deterministically without invoking the LLM.

    This is the strict authorization and deterministic confirmation boundary.
    """
    if datetime.now(UTC) >= pending.expires_at:
        return ConfirmationTurnResult(handled=True, action="expired", pending=None)

    action = classify_confirmation_input(user_input)

    if action == "cancel":
        return ConfirmationTurnResult(handled=True, action="cancelled", pending=None)

    if action != "confirm":
        return ConfirmationTurnResult(handled=False, pending=pending)

    # Validate that beneficiary still exists/valid
    if client is not None:
        # Check against backend client
        search_res = await client.search_beneficiaries(
            user_id="user_001",
            query=pending.beneficiary_id,
        )
        if not search_res and beneficiaries_list:
            # fallback check for demo / mock lists
            found = any(b.get("id") == pending.beneficiary_id for b in beneficiaries_list)
            if not found:
                return ConfirmationTurnResult(
                    handled=True,
                    action="error",
                    pending=None,
                    error="The prepared beneficiary could no longer be verified.",
                )
    elif beneficiaries_list is not None:
        found = any(b.get("id") == pending.beneficiary_id for b in beneficiaries_list)
        if not found:
            return ConfirmationTurnResult(
                handled=True,
                action="error",
                pending=None,
                error="The prepared beneficiary could no longer be verified.",
            )

    # Next boundary: UI Pay PIN / authorization is required before execution.
    # Quanta never executes financial transactions itself.
    return ConfirmationTurnResult(
        handled=True,
        action="authorization_required",
        pending=None,
    )
