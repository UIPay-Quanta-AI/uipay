from datetime import date
from decimal import Decimal

import pytest

from app.domain.budget.models import (
    Budget,
    BudgetAllocation,
    BudgetDomainError,
    GoalAllocation,
    IncomePlan,
)


def test_valid_budget_creation():
    b = Budget(
        id="budget-1",
        user_id="user-001",
        start_date=date(2026, 9, 10),
        end_date=date(2026, 10, 9),
        income_plan=IncomePlan(expected_income=Decimal("300000.00")),
        allocations=[
            BudgetAllocation(category="food", allocated_amount=Decimal("75000.00")),
            BudgetAllocation(category="housing", allocated_amount=Decimal("90000.00")),
        ],
        goal_allocations=[
            GoalAllocation(goal_id="g1", goal_name="Laptop", allocated_amount=Decimal("50000.00")),
        ],
    )

    assert b.start_date == date(2026, 9, 10)
    assert b.end_date == date(2026, 10, 9)
    assert b.total_allocated_expenses == Decimal("165000.00")
    assert b.total_allocated_goals == Decimal("50000.00")
    assert b.total_unallocated_income == Decimal("85000.00")


def test_invalid_dates_start_after_end():
    with pytest.raises(BudgetDomainError, match="must be strictly before"):
        Budget(
            id="budget-1",
            user_id="user-001",
            start_date=date(2026, 10, 10),
            end_date=date(2026, 9, 10),
            income_plan=IncomePlan(expected_income=Decimal("300000.00")),
        )


def test_allocations_exceeding_income_rejection():
    with pytest.raises(BudgetDomainError, match="cannot exceed expected income"):
        Budget(
            id="budget-1",
            user_id="user-001",
            start_date=date(2026, 9, 10),
            end_date=date(2026, 10, 9),
            income_plan=IncomePlan(expected_income=Decimal("100000.00")),
            allocations=[
                BudgetAllocation(category="food", allocated_amount=Decimal("150000.00")),
            ],
        )


def test_remaining_period_calculation():
    b = Budget(
        id="budget-1",
        user_id="user-001",
        start_date=date(2026, 9, 10),
        end_date=date(2026, 10, 9),
        income_plan=IncomePlan(expected_income=Decimal("300000.00")),
    )

    rem_start, rem_end = b.remaining_period(date(2026, 9, 22))
    assert rem_start == date(2026, 9, 22)
    assert rem_end == date(2026, 10, 9)

    with pytest.raises(BudgetDomainError, match="past budget end_date"):
        b.remaining_period(date(2026, 10, 15))


def test_ownership_validation():
    b = Budget(
        id="budget-1",
        user_id="user-001",
        start_date=date(2026, 9, 10),
        end_date=date(2026, 10, 9),
        income_plan=IncomePlan(expected_income=Decimal("300000.00")),
    )

    b.validate_ownership("user-001")
    with pytest.raises(BudgetDomainError, match="ownership mismatch"):
        b.validate_ownership("user-002")
