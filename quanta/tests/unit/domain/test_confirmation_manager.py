from __future__ import annotations

import pytest

from app.domain.confirmation import (
    ConfirmationAlreadyConsumedError,
    ConfirmationExpiredError,
    ConfirmationManager,
    ConfirmationNotFoundError,
    ConfirmationOwnershipError,
    ConfirmationStatus,
    InMemoryConfirmationStore,
    InvalidConfirmationStateError,
)


@pytest.fixture
def confirmation_manager() -> ConfirmationManager:
    store = InMemoryConfirmationStore()
    return ConfirmationManager(store=store, default_ttl_seconds=300)


@pytest.mark.asyncio
async def test_create_and_get_confirmation(confirmation_manager: ConfirmationManager) -> None:
    conf = await confirmation_manager.create(
        request_id="req-1",
        user_id="user_001",
        session_id="sess-100",
        operation="transfer",
        amount=10000,
        prepared_reference="prep-ref-1",
        beneficiary_id="ben_001",
    )

    assert conf.confirmation_id.startswith("conf-")
    assert conf.status == ConfirmationStatus.PENDING
    assert conf.amount == 10000
    assert conf.is_valid_fingerprint()

    retrieved = await confirmation_manager.get(conf.confirmation_id)
    assert retrieved is not None
    assert retrieved.confirmation_id == conf.confirmation_id


@pytest.mark.asyncio
async def test_confirm_lifecycle_and_replay_protection(
    confirmation_manager: ConfirmationManager,
) -> None:
    conf = await confirmation_manager.create(
        request_id="req-1",
        user_id="user_001",
        session_id="sess-100",
        operation="transfer",
        amount=10000,
        prepared_reference="prep-ref-1",
    )

    # 1. PENDING -> CONFIRMED
    confirmed = await confirmation_manager.confirm(
        confirmation_id=conf.confirmation_id,
        user_id="user_001",
        session_id="sess-100",
        operation="transfer",
    )
    assert confirmed.status == ConfirmationStatus.CONFIRMED

    # 2. CONFIRMED -> CONSUMED (Execution boundary)
    consumed = await confirmation_manager.consume(
        confirmation_id=conf.confirmation_id,
        user_id="user_001",
        session_id="sess-100",
        operation="transfer",
    )
    assert consumed.status == ConfirmationStatus.CONSUMED

    # 3. Replay Protection: Second consume attempt must raise ConfirmationAlreadyConsumedError
    with pytest.raises(ConfirmationAlreadyConsumedError):
        await confirmation_manager.consume(
            confirmation_id=conf.confirmation_id,
            user_id="user_001",
            session_id="sess-100",
            operation="transfer",
        )

    # 4. Confirm on consumed record must raise ConfirmationAlreadyConsumedError
    with pytest.raises(ConfirmationAlreadyConsumedError):
        await confirmation_manager.confirm(
            confirmation_id=conf.confirmation_id,
            user_id="user_001",
            session_id="sess-100",
            operation="transfer",
        )


@pytest.mark.asyncio
async def test_user_and_session_ownership_isolation(
    confirmation_manager: ConfirmationManager,
) -> None:
    conf = await confirmation_manager.create(
        request_id="req-1",
        user_id="user_001",
        session_id="sess-100",
        operation="transfer",
        amount=10000,
        prepared_reference="prep-ref-1",
    )

    # User B attempting to confirm User A's record must be rejected
    with pytest.raises(ConfirmationOwnershipError):
        await confirmation_manager.confirm(
            confirmation_id=conf.confirmation_id,
            user_id="user_002",
            session_id="sess-100",
            operation="transfer",
        )

    # Session B attempting to confirm Session A's record must be rejected
    with pytest.raises(ConfirmationOwnershipError):
        await confirmation_manager.confirm(
            confirmation_id=conf.confirmation_id,
            user_id="user_001",
            session_id="sess-999",
            operation="transfer",
        )


@pytest.mark.asyncio
async def test_expiry_handling(confirmation_manager: ConfirmationManager) -> None:
    # Create confirmation with negative TTL (already expired)
    conf = await confirmation_manager.create(
        request_id="req-1",
        user_id="user_001",
        session_id="sess-100",
        operation="transfer",
        amount=10000,
        prepared_reference="prep-ref-1",
        ttl_seconds=-10,
    )

    with pytest.raises(ConfirmationExpiredError):
        await confirmation_manager.confirm(
            confirmation_id=conf.confirmation_id,
            user_id="user_001",
            session_id="sess-100",
            operation="transfer",
        )


@pytest.mark.asyncio
async def test_cancellation_and_invalid_transition(
    confirmation_manager: ConfirmationManager,
) -> None:
    conf = await confirmation_manager.create(
        request_id="req-1",
        user_id="user_001",
        session_id="sess-100",
        operation="transfer",
        amount=10000,
        prepared_reference="prep-ref-1",
    )

    cancelled = await confirmation_manager.cancel(
        confirmation_id=conf.confirmation_id,
        user_id="user_001",
        session_id="sess-100",
        operation="transfer",
    )
    assert cancelled.status == ConfirmationStatus.CANCELLED

    # Attempting to confirm a cancelled record must fail closed
    with pytest.raises(InvalidConfirmationStateError):
        await confirmation_manager.confirm(
            confirmation_id=conf.confirmation_id,
            user_id="user_001",
            session_id="sess-100",
            operation="transfer",
        )


@pytest.mark.asyncio
async def test_not_found_handling(confirmation_manager: ConfirmationManager) -> None:
    with pytest.raises(ConfirmationNotFoundError):
        await confirmation_manager.confirm(
            confirmation_id="nonexistent-id",
            user_id="user_001",
            session_id="sess-100",
            operation="transfer",
        )
