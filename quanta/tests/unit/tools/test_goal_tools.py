from decimal import Decimal

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.schemas.states import QuantaState
from app.services.goal_service import GoalService
from app.tools.base import ToolClassification
from app.tools.executor import ToolExecutor
from app.tools.implementations.goals import (
    CreateGoalInput,
    CreateGoalTool,
    GetGoalInput,
    GetGoalsTool,
    GetGoalTool,
    UpdateGoalInput,
    UpdateGoalTool,
)
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry


@pytest.fixture
def goal_service():
    client = MockUIPayClient()
    return GoalService(client=client)


@pytest.mark.asyncio
async def test_goal_tool_classifications(goal_service):
    create_t = CreateGoalTool(service=goal_service)
    get_all_t = GetGoalsTool(service=goal_service)
    get_one_t = GetGoalTool(service=goal_service)
    update_t = UpdateGoalTool(service=goal_service)

    assert create_t.classification == ToolClassification.WRITE
    assert get_all_t.classification == ToolClassification.SENSITIVE_READ
    assert get_one_t.classification == ToolClassification.SENSITIVE_READ
    assert update_t.classification == ToolClassification.WRITE


@pytest.mark.asyncio
async def test_create_and_get_goal_flow(goal_service):
    context = RequestContext.create(
        user_id="user-001",
        session_id="session-001",
        operation="voice",
    )

    create_t = CreateGoalTool(service=goal_service)
    res_create = await create_t.execute(
        context=context,
        arguments=CreateGoalInput(
            name="Laptop",
            target_amount=Decimal("500000.00"),
        ),
    )

    assert res_create.success is True
    goal_id = res_create.data["id"]
    assert res_create.data["remaining_amount"] == "500000.00"

    get_t = GetGoalTool(service=goal_service)
    res_get = await get_t.execute(
        context=context,
        arguments=GetGoalInput(goal_identifier=goal_id),
    )

    assert res_get.success is True
    assert res_get.data["name"] == "Laptop"
    assert res_get.data["target_amount"] == "500000.00"


@pytest.mark.asyncio
async def test_update_goal_tool_remaining_calculation(goal_service):
    context = RequestContext.create(
        user_id="user-001",
        session_id="session-001",
        operation="voice",
    )

    create_t = CreateGoalTool(service=goal_service)
    res_create = await create_t.execute(
        context=context,
        arguments=CreateGoalInput(
            name="Laptop",
            target_amount=Decimal("500000.00"),
        ),
    )

    goal_id = res_create.data["id"]

    update_t = UpdateGoalTool(service=goal_service)
    res_up = await update_t.execute(
        context=context,
        arguments=UpdateGoalInput(
            goal_identifier=goal_id,
            current_amount=Decimal("320000.00"),
        ),
    )

    assert res_up.success is True
    assert res_up.data["current_amount"] == "320000.00"
    assert res_up.data["remaining_amount"] == "180000.00"


@pytest.mark.asyncio
async def test_goal_tools_via_executor(goal_service):
    registry = ToolRegistry()
    registry.register(CreateGoalTool(service=goal_service))
    registry.register(GetGoalsTool(service=goal_service))
    registry.register(GetGoalTool(service=goal_service))
    registry.register(UpdateGoalTool(service=goal_service))

    executor = ToolExecutor(registry=registry, policy=ToolPolicy())

    context = RequestContext.create(
        user_id="user-001",
        session_id="session-001",
        operation="voice",
    )

    # 1. Create goal
    res1 = await executor.execute(
        tool_name="create_goal",
        arguments={"name": "Rent", "target_amount": 1000000},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res1.success is True

    # 2. Get all goals
    res2 = await executor.execute(
        tool_name="get_goals",
        arguments={},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res2.success is True
    assert res2.data["total_count"] == 1
