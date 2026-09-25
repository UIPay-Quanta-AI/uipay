from __future__ import annotations

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.domain.transfer.account import AccountValidator
from app.domain.transfer.amount import AmountValidator


@pytest.fixture
def mock_client() -> MockUIPayClient:
    return MockUIPayClient(
        beneficiaries=[
            {
                "id": "ben_001",
                "user_id": "user_001",
                "nickname": "Mum",
                "account_name": "Amaka Okafor",
                "bank_name": "GTBank",
                "account_number": "0123456789",
            }
        ]
    )


@pytest.mark.asyncio
async def test_account_validator_success(mock_client: MockUIPayClient) -> None:
    validator = AccountValidator(mock_client)
    ctx = RequestContext.create(user_id="user_001", session_id="s1", operation="val")

    res = await validator.validate(
        bank_code="GTB",
        account_number="0123456789",
        context=ctx,
    )

    assert res.valid
    assert res.account_name == "Amaka Okafor"
    assert res.account_number == "0123456789"
    assert res.bank_name == "GTBank"


@pytest.mark.asyncio
async def test_account_validator_invalid_length(mock_client: MockUIPayClient) -> None:
    validator = AccountValidator(mock_client)
    ctx = RequestContext.create(user_id="user_001", session_id="s1", operation="val")

    res = await validator.validate(
        bank_code="GTB",
        account_number="123",
        context=ctx,
    )

    assert not res.valid
    assert res.error is not None
    assert "10 digits" in res.error


def test_amount_validator_valid_slang() -> None:
    validator = AmountValidator(max_transaction_limit=1_000_000)

    res = validator.validate("send 10k")
    assert res.valid
    assert res.amount == 10_000
    assert res.currency == "NGN"


def test_amount_validator_exceeds_limit() -> None:
    validator = AmountValidator(max_transaction_limit=100_000)

    res = validator.validate("send 200k")
    assert not res.valid
    assert res.error is not None
    assert "exceeds maximum" in res.error
