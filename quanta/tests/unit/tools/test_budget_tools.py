import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.schemas.states import QuantaState
from app.services.budget_service import BudgetService
from app.services.financial_profile_service import FinancialProfileService
from app.services.goal_service import GoalService
from app.tools.base import ToolClassification
from app.tools.executor import ToolExecutor
from app.tools.implementations.budget import (
    GenerateBudgetTool,
    GetBudgetHistoryTool,
    GetCurrentBudgetTool,
    UpdateBudgetTool,
)
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry


@pytest.fixture
def budget_service():
    client = MockUIPayClient()
    p_service = FinancialProfileService(client=client)
    g_service = GoalService(client=client)
    return BudgetService(
        client=client,
        profile_service=p_service,
        goal_service=g_service,
    )


@pytest.mark.asyncio
async def test_budget_tool_classifications(budget_service):
    gen_t = GenerateBudgetTool(service=budget_service)
    up_t = UpdateBudgetTool(service=budget_service)
    cur_t = GetCurrentBudgetTool(service=budget_service)
    hist_t = GetBudgetHistoryTool(service=budget_service)

    assert gen_t.classification == ToolClassification.WRITE
    assert up_t.classification == ToolClassification.WRITE
    assert cur_t.classification == ToolClassification.SENSITIVE_READ
    assert hist_t.classification == ToolClassification.SENSITIVE_READ


@pytest.mark.asyncio
async def test_budget_tools_flow_via_executor(budget_service):
    registry = ToolRegistry()
    registry.register(GenerateBudgetTool(service=budget_service))
    registry.register(UpdateBudgetTool(service=budget_service))
    registry.register(GetCurrentBudgetTool(service=budget_service))
    registry.register(GetBudgetHistoryTool(service=budget_service))

    executor = ToolExecutor(registry=registry, policy=ToolPolicy())

    context = RequestContext.create(
        user_id="user-001",
        session_id="session-001",
        operation="voice",
    )

    # 1. Generate budget
    res_gen = await executor.execute(
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

    # 2. Get current budget
    res_cur = await executor.execute(
        tool_name="get_current_budget",
        arguments={},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_cur.success is True
    assert res_cur.data["budget_exists"] is True
    assert res_cur.data["id"] == b1_id

    # 3. Update budget
    res_up = await executor.execute(
        tool_name="update_budget",
        arguments={
            "budget_id": b1_id,
            "income_update": 450000,
            "update_reason": "income_change",
        },
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_up.success is True
    assert res_up.data["version"] == 2
    assert res_up.data["start_date"] == "2026-09-10"
    assert res_up.data["end_date"] == "2026-10-09"

    # 4. Get history
    res_hist = await executor.execute(
        tool_name="get_budget_history",
        arguments={},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_hist.success is True
    assert res_hist.data["total_count"] == 2
