from datetime import date
from decimal import Decimal

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.domain.budget.models import BudgetStatus, UpdateReason
from app.services.budget_service import BudgetService, BudgetServiceError
from app.services.financial_profile_service import FinancialProfileService
from app.services.goal_service import GoalService


@pytest.fixture
def mock_client():
    return MockUIPayClient()


@pytest.fixture
def budget_service(mock_client):
    profile_service = FinancialProfileService(client=mock_client)
    goal_service = GoalService(client=mock_client)
    return BudgetService(
        client=mock_client,
        profile_service=profile_service,
        goal_service=goal_service,
    )


@pytest.mark.asyncio
async def test_generate_budget_without_transaction_context(budget_service):
    b = await budget_service.generate_budget(
        user_id="user-001",
        start_date=date(2026, 9, 10),
        end_date=date(2026, 10, 9),
    )

    assert b.user_id == "user-001"
    assert b.start_date == date(2026, 9, 10)
    assert b.end_date == date(2026, 10, 9)
    assert b.version == 1
    assert b.status == BudgetStatus.ACTIVE
    assert b.income_plan.expected_income == Decimal("300000.00")
    assert len(b.allocations) > 0


@pytest.mark.asyncio
async def test_generate_budget_with_goals_integration(mock_client, budget_service):
    goal_service = GoalService(client=mock_client)
    await goal_service.create_goal(
        user_id="user-001",
        name="Laptop",
        target_amount=Decimal("500000.00"),
    )

    b = await budget_service.generate_budget(
        user_id="user-001",
        start_date=date(2026, 9, 10),
        end_date=date(2026, 10, 9),
    )

    assert len(b.goal_allocations) == 1
    assert b.goal_allocations[0].goal_name == "Laptop"


@pytest.mark.asyncio
async def test_update_budget_preserves_original_period_and_creates_v2(budget_service):
    v1 = await budget_service.generate_budget(
        user_id="user-001",
        start_date=date(2026, 9, 10),
        end_date=date(2026, 10, 9),
    )

    v2, prev = await budget_service.update_budget(
        user_id="user-001",
        budget_id=v1.id,
        as_of_date=date(2026, 9, 22),
        income_update=Decimal("400000.00"),
        update_reason=UpdateReason.INCOME_CHANGE,
    )

    # CRITICAL: Original start and end date preserved!
    assert v2.start_date == date(2026, 9, 10)
    assert v2.end_date == date(2026, 10, 9)
    assert v2.version == 2
    assert v2.previous_version_id == v1.id
    assert v2.income_plan.expected_income == Decimal("400000.00")
    assert v2.status == BudgetStatus.ACTIVE

    # Previous version is superseded
    assert prev.id == v1.id


@pytest.mark.asyncio
async def test_cross_user_budget_isolation(budget_service):
    b1 = await budget_service.generate_budget(
        user_id="user-001",
        start_date=date(2026, 9, 10),
        end_date=date(2026, 10, 9),
    )

    with pytest.raises(BudgetServiceError, match="No active budget found"):
        await budget_service.update_budget(
            user_id="user-002",
            budget_id=b1.id,
            income_update=Decimal("500000.00"),
        )
