from decimal import Decimal

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.domain.goals.models import GoalStatus
from app.services.goal_service import GoalService, GoalServiceError


@pytest.mark.asyncio
async def test_create_goal_success():
    client = MockUIPayClient()
    service = GoalService(client=client)

    goal = await service.create_goal(
        user_id="user-001",
        name="Save for Laptop",
        target_amount=Decimal("500000.00"),
    )

    assert goal.name == "Save for Laptop"
    assert goal.target_amount == Decimal("500000.00")
    assert goal.current_amount == Decimal("0.00")
    assert goal.remaining_amount == Decimal("500000.00")
    assert goal.status == GoalStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_goals_user_isolation():
    client = MockUIPayClient()
    service = GoalService(client=client)

    await service.create_goal(
        user_id="user-001",
        name="Laptop Goal User 1",
        target_amount=Decimal("500000.00"),
    )
    await service.create_goal(
        user_id="user-002",
        name="Rent Goal User 2",
        target_amount=Decimal("1000000.00"),
    )

    goals_u1 = await service.get_goals(user_id="user-001")
    goals_u2 = await service.get_goals(user_id="user-002")

    assert len(goals_u1) == 1
    assert goals_u1[0].name == "Laptop Goal User 1"

    assert len(goals_u2) == 1
    assert goals_u2[0].name == "Rent Goal User 2"


@pytest.mark.asyncio
async def test_update_goal_progress_and_remaining():
    client = MockUIPayClient()
    service = GoalService(client=client)

    created = await service.create_goal(
        user_id="user-001",
        name="Laptop",
        target_amount=Decimal("500000.00"),
    )

    updated = await service.update_goal(
        user_id="user-001",
        goal_identifier=created.id,
        updates={"current_amount": Decimal("320000.00")},
    )

    assert updated.current_amount == Decimal("320000.00")
    assert updated.remaining_amount == Decimal("180000.00")


@pytest.mark.asyncio
async def test_cross_user_goal_access_prevented():
    client = MockUIPayClient()
    service = GoalService(client=client)

    created = await service.create_goal(
        user_id="user-001",
        name="Secret Goal",
        target_amount=Decimal("100000.00"),
    )

    with pytest.raises(GoalServiceError, match="not found for user 'user-002'"):
        await service.get_goal(user_id="user-002", goal_identifier=created.id)
