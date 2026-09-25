import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.dependencies.tools import build_tool_registry
from app.schemas.states import QuantaState
from app.tools.executor import ToolExecutor
from app.tools.policy import ToolPolicy


@pytest.fixture
def mock_client():
    return MockUIPayClient()


@pytest.fixture
def tool_executor(mock_client):
    registry = build_tool_registry(ui_pay_client=mock_client)
    policy = ToolPolicy()
    return ToolExecutor(registry=registry, policy=policy)


@pytest.mark.asyncio
async def test_step16_financial_profile_e2e_flow(tool_executor):
    context = RequestContext.create(
        user_id="user_001",
        session_id="session_100",
        operation="voice",
    )

    # 1. "What is my financial profile?" -> get_financial_profile
    res_get = await tool_executor.execute(
        tool_name="get_financial_profile",
        arguments={},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_get.success is True
    assert res_get.data["monthly_income"] == "300000.00"
    assert res_get.data["currency"] == "NGN"

    # 2. "Update my monthly income to 350,000 naira." -> update_financial_profile
    res_up = await tool_executor.execute(
        tool_name="update_financial_profile",
        arguments={"monthly_income": 350000},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_up.success is True
    assert res_up.data["monthly_income"] == "350000.00"
    assert "monthly_income" in res_up.data["updated_fields"]


@pytest.mark.asyncio
async def test_step17_financial_goals_e2e_flow(tool_executor):
    context = RequestContext.create(
        user_id="user_001",
        session_id="session_100",
        operation="voice",
    )

    # 1. "Create a goal to save ₦500,000 for a laptop."
    res_create = await tool_executor.execute(
        tool_name="create_goal",
        arguments={"name": "laptop", "target_amount": 500000},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_create.success is True
    goal_id = res_create.data["id"]
    assert res_create.data["remaining_amount"] == "500000.00"

    # 2. "How much do I have left for my laptop goal?" -> update saved amount to 320k
    res_progress = await tool_executor.execute(
        tool_name="update_goal",
        arguments={"goal_identifier": goal_id, "current_amount": 320000},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_progress.success is True
    assert res_progress.data["current_amount"] == "320000.00"
    assert res_progress.data["remaining_amount"] == "180000.00"

    # 3. "Update my laptop goal to ₦700,000."
    res_update_target = await tool_executor.execute(
        tool_name="update_goal",
        arguments={"goal_identifier": goal_id, "target_amount": 700000},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_update_target.success is True
    assert res_update_target.data["target_amount"] == "700000.00"
    assert res_update_target.data["remaining_amount"] == "380000.00"


@pytest.mark.asyncio
async def test_profile_and_goals_coexist_independently_with_cross_user_isolation(tool_executor):
    u1_ctx = RequestContext.create(
        user_id="user_001",
        session_id="session_101",
        operation="voice",
    )
    u2_ctx = RequestContext.create(
        user_id="user_002",
        session_id="session_102",
        operation="voice",
    )

    # User 1 updates income and creates goal
    await tool_executor.execute(
        tool_name="update_financial_profile",
        arguments={"monthly_income": 600000},
        context=u1_ctx,
        state=QuantaState.IDLE,
    )
    res_g1 = await tool_executor.execute(
        tool_name="create_goal",
        arguments={"name": "Vacation", "target_amount": 200000},
        context=u1_ctx,
        state=QuantaState.IDLE,
    )

    # User 2 gets profile (must receive default user_002 profile, not user_001)
    res_p2 = await tool_executor.execute(
        tool_name="get_financial_profile",
        arguments={},
        context=u2_ctx,
        state=QuantaState.IDLE,
    )
    assert res_p2.data["monthly_income"] == "300000.00"  # Default mock value for user_002

    # User 2 lists goals (must be 0, user_001 goal must not leak)
    res_g2 = await tool_executor.execute(
        tool_name="get_goals",
        arguments={},
        context=u2_ctx,
        state=QuantaState.IDLE,
    )
    assert res_g2.data["total_count"] == 0

    # User 2 cannot retrieve user 1's goal
    res_g2_one = await tool_executor.execute(
        tool_name="get_goal",
        arguments={"goal_identifier": res_g1.data["id"]},
        context=u2_ctx,
        state=QuantaState.IDLE,
    )
    assert res_g2_one.success is False
    assert res_g2_one.error_code == "GET_GOAL_FAILED"
