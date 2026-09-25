from decimal import Decimal

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.domain.financial_profile.models import EmploymentType
from app.services.financial_profile_service import (
    FinancialProfileService,
    FinancialProfileServiceError,
)


@pytest.mark.asyncio
async def test_get_profile_success():
    client = MockUIPayClient()
    service = FinancialProfileService(client=client)

    profile = await service.get_profile(user_id="user-001")

    assert profile.user_id == "user-001"
    assert profile.currency == "NGN"
    assert profile.monthly_income == Decimal("300000.00")


@pytest.mark.asyncio
async def test_update_profile_success():
    client = MockUIPayClient()
    service = FinancialProfileService(client=client)

    updated_profile, updated_fields = await service.update_profile(
        user_id="user-001",
        updates={
            "monthly_income": Decimal("400000.00"),
            "employment_type": EmploymentType.FREELANCE,
        },
    )

    assert updated_profile.monthly_income == Decimal("400000.00")
    assert updated_profile.employment_type == EmploymentType.FREELANCE
    assert "monthly_income" in updated_fields
    assert "employment_type" in updated_fields


@pytest.mark.asyncio
async def test_update_profile_ignores_disallowed_or_empty_updates():
    client = MockUIPayClient()
    service = FinancialProfileService(client=client)

    with pytest.raises(FinancialProfileServiceError, match="No valid profile fields provided"):
        await service.update_profile(
            user_id="user-001",
            updates={"unknown_field": "test"},
        )


@pytest.mark.asyncio
async def test_get_profile_empty_user_id_error():
    client = MockUIPayClient()
    service = FinancialProfileService(client=client)

    with pytest.raises(FinancialProfileServiceError, match="User identity context is required"):
        await service.get_profile(user_id="")
