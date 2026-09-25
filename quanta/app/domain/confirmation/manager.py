from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.confirmation.errors import (
    ConfirmationAlreadyConsumedError,
    ConfirmationExpiredError,
    ConfirmationNotFoundError,
    ConfirmationOwnershipError,
    InvalidConfirmationStateError,
)
from app.domain.confirmation.models import Confirmation, ConfirmationStatus
from app.domain.confirmation.store import ConfirmationStore

CONFIRMATION_DEFAULT_TTL_SECONDS = 300


class ConfirmationManager:
    """
    Manages the lifecycle of transfer confirmation records.

    Responsible for validation, status transitions, TTL enforcement, and replay prevention.
    """

    def __init__(
        self,
        *,
        store: ConfirmationStore,
        default_ttl_seconds: int = CONFIRMATION_DEFAULT_TTL_SECONDS,
    ) -> None:
        self._store = store
        self._default_ttl_seconds = default_ttl_seconds

    async def create(
        self,
        *,
        request_id: str,
        user_id: str,
        session_id: str,
        operation: str,
        amount: int,
        prepared_reference: str,
        currency: str = "NGN",
        beneficiary_id: str | None = None,
        account_number: str | None = None,
        ttl_seconds: int | None = None,
    ) -> Confirmation:
        """Create a new pending confirmation record."""
        now = datetime.now(UTC)
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        expires_at = now + timedelta(seconds=ttl)

        confirmation = Confirmation(
            confirmation_id=f"conf-{uuid4().hex[:12]}",
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
            operation=operation,
            amount=amount,
            currency=currency,
            prepared_reference=prepared_reference,
            created_at=now,
            expires_at=expires_at,
            beneficiary_id=beneficiary_id,
            account_number=account_number,
            status=ConfirmationStatus.PENDING,
        )

        return await self._store.create(confirmation)

    async def get(self, confirmation_id: str) -> Confirmation | None:
        """Retrieve a confirmation record by ID."""
        return await self._store.get(confirmation_id)

    async def find_latest_pending(
        self,
        user_id: str,
        session_id: str,
    ) -> Confirmation | None:
        """Find active pending confirmation for a user session."""
        return await self._store.find_latest_pending(user_id, session_id)

    async def validate(
        self,
        *,
        confirmation_id: str,
        user_id: str,
        session_id: str,
        operation: str,
    ) -> Confirmation:
        """
        Validate ownership, state, TTL expiry, and integrity of a confirmation record.
        """
        confirmation = await self._store.get(confirmation_id)
        if confirmation is None:
            raise ConfirmationNotFoundError(f"Confirmation {confirmation_id} not found.")

        if confirmation.user_id != user_id or confirmation.session_id != session_id:
            raise ConfirmationOwnershipError("Confirmation ownership mismatch.")

        if confirmation.operation != operation:
            raise ConfirmationOwnershipError(
                f"Confirmation operation mismatch ({confirmation.operation} vs {operation})."
            )

        if not confirmation.is_valid_fingerprint():
            raise InvalidConfirmationStateError("Confirmation integrity fingerprint invalid.")

        if datetime.now(UTC) >= confirmation.expires_at:
            confirmation.status = ConfirmationStatus.EXPIRED
            await self._store.update(confirmation)
            raise ConfirmationExpiredError("Confirmation has expired.")

        if confirmation.status == ConfirmationStatus.CONSUMED:
            raise ConfirmationAlreadyConsumedError("Confirmation has already been consumed.")

        if confirmation.status != ConfirmationStatus.PENDING:
            raise InvalidConfirmationStateError(
                f"Confirmation is in invalid state {confirmation.status.value}."
            )

        return confirmation

    async def confirm(
        self,
        *,
        confirmation_id: str,
        user_id: str,
        session_id: str,
        operation: str,
    ) -> Confirmation:
        """
        Transition pending confirmation to CONFIRMED.

        This authorizes entry into the downstream UI Pay execution boundary.
        """
        record = await self.validate(
            confirmation_id=confirmation_id,
            user_id=user_id,
            session_id=session_id,
            operation=operation,
        )

        record.status = ConfirmationStatus.CONFIRMED
        return await self._store.update(record)

    async def cancel(
        self,
        *,
        confirmation_id: str,
        user_id: str,
        session_id: str,
        operation: str,
    ) -> Confirmation:
        """Transition pending confirmation to CANCELLED."""
        record = await self._store.get(confirmation_id)
        if record is None:
            raise ConfirmationNotFoundError(f"Confirmation {confirmation_id} not found.")

        if record.user_id != user_id or record.session_id != session_id:
            raise ConfirmationOwnershipError("Confirmation ownership mismatch.")

        record.status = ConfirmationStatus.CANCELLED
        return await self._store.update(record)

    async def expire(self, confirmation_id: str) -> Confirmation:
        """Transition pending confirmation to EXPIRED."""
        record = await self._store.get(confirmation_id)
        if record is None:
            raise ConfirmationNotFoundError(f"Confirmation {confirmation_id} not found.")

        record.status = ConfirmationStatus.EXPIRED
        return await self._store.update(record)

    async def consume(
        self,
        *,
        confirmation_id: str,
        user_id: str,
        session_id: str,
        operation: str,
    ) -> Confirmation:
        """
        Mark a CONFIRMED record as CONSUMED to prevent replay attacks.
        """
        record = await self._store.get(confirmation_id)
        if record is None:
            raise ConfirmationNotFoundError(f"Confirmation {confirmation_id} not found.")

        if record.user_id != user_id or record.session_id != session_id:
            raise ConfirmationOwnershipError("Confirmation ownership mismatch.")

        if record.status == ConfirmationStatus.CONSUMED:
            raise ConfirmationAlreadyConsumedError("Confirmation has already been consumed.")

        if record.status != ConfirmationStatus.CONFIRMED:
            raise InvalidConfirmationStateError(
                f"Cannot consume confirmation in status {record.status.value}."
            )

        record.status = ConfirmationStatus.CONSUMED
        return await self._store.update(record)
