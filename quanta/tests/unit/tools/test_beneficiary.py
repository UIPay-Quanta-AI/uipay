import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.tools.implementations.beneficiary import (
    SearchBeneficiaryInput,
    SearchBeneficiaryTool,
)


@pytest.fixture
def beneficiaries():
    return [
        {
            "id": "beneficiary-1",
            "user_id": "user-123",
            "nickname": "Mum",
            "account_name": "Amaka Okafor",
            "bank_name": "GTBank",
            "account_number": "0123456789",
        },
        {
            "id": "beneficiary-2",
            "user_id": "user-123",
            "nickname": "Brother",
            "account_name": "Chinedu Okafor",
            "bank_name": "Access Bank",
            "account_number": "9876543210",
        },
        {
            "id": "beneficiary-3",
            "user_id": "another-user",
            "nickname": "Mum",
            "account_name": "Another User",
            "bank_name": "GTBank",
            "account_number": "1111111111",
        },
    ]


@pytest.mark.asyncio
async def test_search_beneficiary_by_nickname(beneficiaries):
    client = MockUIPayClient(
        beneficiaries=beneficiaries,
    )

    tool = SearchBeneficiaryTool(
        client=client,
    )

    context = RequestContext.create(
        user_id="user-123",
        session_id="session-123",
        operation="voice",
    )

    result = await tool.execute(
        context=context,
        arguments=SearchBeneficiaryInput(
            query="Mum",
        ),
    )

    assert result.success is True
    assert result.data is not None

    found = result.data["beneficiaries"]

    assert len(found) == 1
    assert found[0]["account_name"] == "Amaka Okafor"


@pytest.mark.asyncio
async def test_beneficiary_search_respects_authenticated_user(
    beneficiaries,
):
    client = MockUIPayClient(
        beneficiaries=beneficiaries,
    )

    tool = SearchBeneficiaryTool(
        client=client,
    )

    context = RequestContext.create(
        user_id="user-123",
        session_id="session-123",
        operation="voice",
    )

    result = await tool.execute(
        context=context,
        arguments=SearchBeneficiaryInput(
            query="Mum",
        ),
    )

    found = result.data["beneficiaries"]

    assert all(item["account_name"] != "Another User" for item in found)


@pytest.mark.asyncio
async def test_search_beneficiary_by_account_name(
    beneficiaries,
):
    client = MockUIPayClient(
        beneficiaries=beneficiaries,
    )

    tool = SearchBeneficiaryTool(
        client=client,
    )

    context = RequestContext.create(
        user_id="user-123",
        session_id="session-123",
        operation="voice",
    )

    result = await tool.execute(
        context=context,
        arguments=SearchBeneficiaryInput(
            query="Chinedu",
        ),
    )

    found = result.data["beneficiaries"]

    assert len(found) == 1
    assert found[0]["nickname"] == "Brother"
