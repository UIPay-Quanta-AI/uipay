from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.schemas.confirmation import (
    PendingConfirmation,
    classify_confirmation_input,
    is_cancellation,
    is_confirmation,
)
from app.services.confirmation_service import handle_pending_confirmation


@pytest.mark.parametrize(
    "phrase",
    [
        "yes",
        "yes send it",
        "confirm",
        "confirmed",
        "proceed",
        "go ahead",
        "ok",
        "yes send am",  # Pidgin
        "bẹẹni",  # Yoruba
        "bẹ́ẹ̀ni tẹ́síwájú",  # Yoruba with diacritics
        "eh ci gaba",  # Hausa
        "ee gaa n'ihu",  # Igbo
    ],
)
def test_is_confirmation_multilingual(phrase: str) -> None:
    assert is_confirmation(phrase)
    assert classify_confirmation_input(phrase) == "confirm"


@pytest.mark.parametrize(
    "phrase",
    [
        "no",
        "cancel",
        "stop",
        "don't send it",
        "no send am",  # Pidgin
        "rara fagilee re",  # Yoruba
        "a'a soke shi",  # Hausa
        "mba kagbuo ya",  # Igbo
    ],
)
def test_is_cancellation_multilingual(phrase: str) -> None:
    assert is_cancellation(phrase)
    assert classify_confirmation_input(phrase) == "cancel"


@pytest.mark.asyncio
async def test_handle_pending_confirmation_confirm() -> None:
    now = datetime.now(UTC)
    pending = PendingConfirmation(
        reference="prep-12345",
        beneficiary_id="ben_001",
        amount=10000,
        currency="NGN",
        created_at=now,
        expires_at=now + timedelta(minutes=5),
    )

    res = await handle_pending_confirmation(
        user_input="yes, send it",
        pending=pending,
        beneficiaries_list=[{"id": "ben_001", "nickname": "Mum"}],
    )

    assert res.handled
    assert res.action == "authorization_required"
    assert res.pending is None


@pytest.mark.asyncio
async def test_handle_pending_confirmation_cancel() -> None:
    now = datetime.now(UTC)
    pending = PendingConfirmation(
        reference="prep-12345",
        beneficiary_id="ben_001",
        amount=10000,
        currency="NGN",
        created_at=now,
        expires_at=now + timedelta(minutes=5),
    )

    res = await handle_pending_confirmation(
        user_input="cancel am",
        pending=pending,
    )

    assert res.handled
    assert res.action == "cancelled"
    assert res.pending is None


@pytest.mark.asyncio
async def test_handle_pending_confirmation_expired() -> None:
    now = datetime.now(UTC) - timedelta(minutes=10)
    pending = PendingConfirmation(
        reference="prep-12345",
        beneficiary_id="ben_001",
        amount=10000,
        currency="NGN",
        created_at=now - timedelta(minutes=5),
        expires_at=now,
    )

    res = await handle_pending_confirmation(
        user_input="yes confirm",
        pending=pending,
    )

    assert res.handled
    assert res.action == "expired"
    assert res.pending is None
