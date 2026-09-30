"""
Unit tests for BudgetService integration with TransactionBudgetContext, versioning, and goals.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.domain.budget.models import BudgetStatus, UpdateReason
from app.domain.goals.models import GoalStatus
from app.services.budget_service import BudgetService
from app.services.financial_profile_service import FinancialProfileService
from app.services.goal_service import GoalService


@pytest.fixture
def mock_client():
    return MockUIPayClient()


@pytest.fixture
def profile_service(mock_client):
    return FinancialProfileService(client=mock_client)


@pytest.fixture
def goal_service(mock_client):
    return GoalService(client=mock_client)


@pytest.fixture
def budget_service(mock_client, profile_service, goal_service):
    return BudgetService(
        client=mock_client,
        profile_service=profile_service,
        goal_service=goal_service,
    )


@pytest.mark.asyncio
async def test_budget_generation_without_transaction_history(budget_service):
    """Verify budget generation when no transaction context exists (data_available=False)."""
    user_id = "user_no_tx"
    budget = await budget_service.generate_budget(
        user_id=user_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert budget.user_id == user_id
    assert budget.version == 1
    assert budget.status == BudgetStatus.ACTIVE
    assert budget.income_plan.expected_income == Decimal("300000.00")
    assert "transaction_history" not in budget.income_plan.income_sources
    assert len(budget.allocations) > 0


@pytest.mark.asyncio
async def test_budget_generation_consumes_transaction_budget_context(
    mock_client, profile_service, goal_service
):
    """Verify that BudgetService meaningfully consumes category trends from TransactionBudgetContext."""
    user_id = "user_tx_context"
    # Inject rich historical transaction context into mock client
    mock_client._transaction_contexts[user_id] = {
        "data_available": True,
        "trends": {
            "category_percentages": {
                "transport": "0.40",
                "food": "0.30",
                "housing": "0.20",
                "utilities": "0.10",
            },
            "observed_income": "500000.00",
        },
        "notable_changes": ["Transport spending increased by 35% in recent period."],
    }

    budget_svc = BudgetService(
        client=mock_client,
        profile_service=profile_service,
        goal_service=goal_service,
    )

    budget = await budget_svc.generate_budget(
        user_id=user_id,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
    )

    assert budget.user_id == user_id
    assert "transaction_history" in budget.income_plan.income_sources
    alloc_map = {a.category: a.allocated_amount for a in budget.allocations}

    # Verify transport allocation reflects historical 40% weight
    assert alloc_map["transport"] > alloc_map["housing"]
    assert alloc_map["transport"] > alloc_map["food"]


@pytest.mark.asyncio
async def test_budget_versioning_and_superseded_status(budget_service, mock_client):
    """Verify updating a budget increments version and marks previous active version as SUPERSEDED."""
    user_id = "user_versioning"
    # Generate Initial Budget (v1)
    b1 = await budget_service.generate_budget(
        user_id=user_id,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
    )
    assert b1.version == 1
    assert b1.status == BudgetStatus.ACTIVE

    # Update Budget (v2)
    b2, _previous = await budget_service.update_budget(
        user_id=user_id,
        budget_id=b1.id,
        income_update=Decimal("400000.00"),
        update_reason=UpdateReason.INCOME_CHANGE,
    )

    assert b2.version == 2
    assert b2.status == BudgetStatus.ACTIVE
    assert b2.previous_version_id == b1.id
    assert b2.start_date == b1.start_date  # Preserves period!
    assert b2.end_date == b1.end_date

    # Verify storage: current budget is v2, history contains v1 (superseded) and v2 (active)
    current = await budget_service.get_current_budget(user_id=user_id)
    assert current.id == b2.id
    assert current.version == 2

    history = await budget_service.get_budget_history(user_id=user_id)
    assert len(history) == 2
    v1_in_hist = next(b for b in history if b.version == 1)
    assert v1_in_hist.status == BudgetStatus.SUPERSEDED


@pytest.mark.asyncio
async def test_budget_does_not_mutate_goal_status(budget_service, goal_service):
    """Verify that budget allocations toward goals do NOT mutate goal status."""
    user_id = "user_goal_budget"
    goal = await goal_service.create_goal(
        user_id=user_id,
        name="Laptop Savings",
        target_amount=Decimal("200000.00"),
    )
    assert goal.status == GoalStatus.ACTIVE

    # Generate budget allocating income to goals
    budget = await budget_service.generate_budget(
        user_id=user_id,
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )
    assert len(budget.goal_allocations) > 0

    # Re-fetch goal to confirm status remains ACTIVE and untouched
    refetched_goal = await goal_service.get_goal(user_id=user_id, goal_identifier=goal.id)
    assert refetched_goal.status == GoalStatus.ACTIVE
