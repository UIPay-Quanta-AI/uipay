from decimal import Decimal

import pytest

from app.domain.goals.models import (
    FinancialGoal,
    GoalDomainError,
    GoalStatus,
)


def test_valid_financial_goal_creation():
    goal = FinancialGoal(
        id="goal-1",
        user_id="user-001",
        name="Laptop",
        target_amount=Decimal("500000.00"),
        current_amount=Decimal("320000.00"),
        status=GoalStatus.ACTIVE,
    )

    assert goal.name == "Laptop"
    assert goal.remaining_amount == Decimal("180000.00")
    assert goal.currency == "NGN"


from pydantic import ValidationError


def test_invalid_target_amount_zero_or_negative():
    with pytest.raises((GoalDomainError, ValidationError)):
        FinancialGoal(
            id="goal-1",
            user_id="user-001",
            name="Laptop",
            target_amount=Decimal("0.00"),
        )


def test_invalid_current_amount_exceeding_target():
    with pytest.raises(GoalDomainError, match="cannot exceed target amount"):
        FinancialGoal(
            id="goal-1",
            user_id="user-001",
            name="Laptop",
            target_amount=Decimal("500000.00"),
            current_amount=Decimal("600000.00"),
        )


def test_invalid_currency_rejection():
    with pytest.raises(GoalDomainError, match="Unsupported goal currency"):
        FinancialGoal(
            id="goal-1",
            user_id="user-001",
            name="Laptop",
            target_amount=Decimal("500000.00"),
            currency="USD",
        )


def test_cancelled_goal_update_restriction():
    goal = FinancialGoal(
        id="goal-1",
        user_id="user-001",
        name="Laptop",
        target_amount=Decimal("500000.00"),
        status=GoalStatus.CANCELLED,
    )

    with pytest.raises(GoalDomainError, match="Cancelled goals cannot be updated"):
        goal.validate_update(new_current_amount=Decimal("100000.00"))


def test_completed_goal_update_restriction():
    goal = FinancialGoal(
        id="goal-1",
        user_id="user-001",
        name="Laptop",
        target_amount=Decimal("500000.00"),
        current_amount=Decimal("500000.00"),
        status=GoalStatus.COMPLETED,
    )

    with pytest.raises(
        GoalDomainError, match="Completed goals cannot receive ordinary progress updates"
    ):
        goal.validate_update(new_current_amount=Decimal("200000.00"))


def test_goal_ownership_validation():
    goal = FinancialGoal(
        id="goal-1",
        user_id="user-001",
        name="Laptop",
        target_amount=Decimal("500000.00"),
    )

    goal.validate_ownership("user-001")

    with pytest.raises(GoalDomainError, match="Goal ownership mismatch"):
        goal.validate_ownership("user-002")
