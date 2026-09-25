from decimal import Decimal

import pytest

from app.domain.financial_profile.models import (
    EmploymentType,
    FinancialProfile,
    FinancialProfileDomainError,
    IncomeFrequency,
)


def test_valid_financial_profile_creation():
    profile = FinancialProfile(
        user_id="user-001",
        monthly_income=Decimal("350000.00"),
        income_frequency=IncomeFrequency.MONTHLY,
        employment_type=EmploymentType.SALARIED,
        fixed_expenses=Decimal("150000.00"),
        variable_expenses=Decimal("80000.00"),
        savings_target=Decimal("50000.00"),
        currency="NGN",
    )

    assert profile.user_id == "user-001"
    assert profile.monthly_income == Decimal("350000.00")
    assert profile.currency == "NGN"


from pydantic import ValidationError


def test_invalid_negative_monetary_values():
    with pytest.raises((FinancialProfileDomainError, ValidationError)):
        FinancialProfile(
            user_id="user-001",
            monthly_income=Decimal("-1000.00"),
        )


def test_invalid_currency_rejection():
    with pytest.raises((FinancialProfileDomainError, ValidationError)):
        FinancialProfile(
            user_id="user-001",
            currency="USD",
        )


def test_empty_user_id_rejection():
    with pytest.raises((FinancialProfileDomainError, ValidationError)):
        FinancialProfile(
            user_id="",
        )


def test_ownership_validation():
    profile = FinancialProfile(
        user_id="user-001",
    )

    profile.validate_ownership("user-001")

    with pytest.raises(FinancialProfileDomainError):
        profile.validate_ownership("user-002")
