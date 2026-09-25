import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.dependencies.tools import build_tool_registry
from app.schemas.states import QuantaState
from app.tools.executor import ToolExecutor
from app.tools.policy import ToolPolicy


@pytest.fixture
def mock_client():
    client = MockUIPayClient()
    # Add optional transaction context for testing
    client._transaction_contexts["user_001"] = {
        "data_available": True,
        "lookback_period": {"start_date": "2025-10-01", "end_date": "2026-09-30"},
        "historical_periods": [
            {
                "period": {"start_date": "2026-08-01", "end_date": "2026-08-31"},
                "observed_income": 350000,
                "observed_expenses": 200000,
                "spending_by_category": {"food": 60000, "housing": 100000},
            }
        ],
        "trends": {"income_trend": "stable", "expense_trend": "stable"},
    }
    return client


@pytest.fixture
def tool_executor(mock_client):
    registry = build_tool_registry(ui_pay_client=mock_client)
    policy = ToolPolicy()
    return ToolExecutor(registry=registry, policy=policy)


@pytest.mark.asyncio
async def test_budget_full_e2e_workflow(tool_executor):
    context = RequestContext.create(
        user_id="user_001",
        session_id="session_100",
        operation="voice",
    )

    # 1. Generate budget for Sep 10 -> Oct 9
    res_gen = await tool_executor.execute(
        tool_name="generate_budget",
        arguments={
            "start_date": "2026-09-10",
            "end_date": "2026-10-09",
        },
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_gen.success is True
    b1_id = res_gen.data["id"]
    assert res_gen.data["version"] == 1
    assert res_gen.data["start_date"] == "2026-09-10"
    assert res_gen.data["end_date"] == "2026-10-09"

    # 2. Retrieve current budget
    res_cur = await tool_executor.execute(
        tool_name="get_current_budget",
        arguments={},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_cur.success is True
    assert res_cur.data["budget_exists"] is True
    assert res_cur.data["id"] == b1_id

    # 3. User updates budget on Sep 22 ("I received an extra ₦100,000")
    res_up = await tool_executor.execute(
        tool_name="update_budget",
        arguments={
            "budget_id": b1_id,
            "as_of_date": "2026-09-22",
            "income_update": 400000,
            "update_reason": "income_change",
        },
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_up.success is True
    # Verify version 2 created and original dates preserved!
    assert res_up.data["version"] == 2
    assert res_up.data["start_date"] == "2026-09-10"
    assert res_up.data["end_date"] == "2026-10-09"
    assert res_up.data["previous_version_id"] == b1_id

    # 4. Get budget history
    res_hist = await tool_executor.execute(
        tool_name="get_budget_history",
        arguments={},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_hist.success is True
    budgets = res_hist.data["budgets"]
    assert len(budgets) == 2
    assert budgets[0]["status"] == "superseded"
    assert budgets[1]["status"] == "active"


@pytest.mark.asyncio
async def test_budget_generation_without_transaction_context(tool_executor):
    u2_ctx = RequestContext.create(
        user_id="user_002",
        session_id="session_200",
        operation="voice",
    )

    # user_002 has no transaction context (data_available=False)
    res_gen = await tool_executor.execute(
        tool_name="generate_budget",
        arguments={
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
        },
        context=u2_ctx,
        state=QuantaState.IDLE,
    )
    assert res_gen.success is True
    assert res_gen.data["version"] == 1
    assert res_gen.data["income_plan"]["expected_income"] == "300000.00"
