from decimal import Decimal

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.schemas.states import QuantaState
from app.services.financial_profile_service import FinancialProfileService
from app.tools.base import ToolClassification
from app.tools.executor import ToolExecutor
from app.tools.implementations.financial_profile import (
    GetFinancialProfileInput,
    GetFinancialProfileTool,
    UpdateFinancialProfileInput,
    UpdateFinancialProfileTool,
)
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry


@pytest.fixture
def profile_service():
    client = MockUIPayClient()
    return FinancialProfileService(client=client)


@pytest.mark.asyncio
async def test_get_financial_profile_tool_classification(profile_service):
    tool = GetFinancialProfileTool(service=profile_service)
    assert tool.classification == ToolClassification.SENSITIVE_READ
    assert tool.name == "get_financial_profile"


@pytest.mark.asyncio
async def test_update_financial_profile_tool_classification(profile_service):
    tool = UpdateFinancialProfileTool(service=profile_service)
    assert tool.classification == ToolClassification.WRITE
    assert tool.name == "update_financial_profile"


@pytest.mark.asyncio
async def test_get_financial_profile_tool_execution(profile_service):
    tool = GetFinancialProfileTool(service=profile_service)
    context = RequestContext.create(
        user_id="user-001",
        session_id="session-001",
        operation="voice",
    )

    result = await tool.execute(
        context=context,
        arguments=GetFinancialProfileInput(),
    )

    assert result.success is True
    assert result.data["monthly_income"] == "300000.00"
    assert result.data["currency"] == "NGN"


@pytest.mark.asyncio
async def test_update_financial_profile_tool_execution(profile_service):
    tool = UpdateFinancialProfileTool(service=profile_service)
    context = RequestContext.create(
        user_id="user-001",
        session_id="session-001",
        operation="voice",
    )

    result = await tool.execute(
        context=context,
        arguments=UpdateFinancialProfileInput(
            monthly_income=Decimal("350000.00"),
            savings_target=Decimal("60000.00"),
        ),
    )

    assert result.success is True
    assert result.data["monthly_income"] == "350000.00"
    assert result.data["savings_target"] == "60000.00"
    assert "monthly_income" in result.data["updated_fields"]


@pytest.mark.asyncio
async def test_financial_profile_tools_via_executor(profile_service):
    registry = ToolRegistry()
    registry.register(GetFinancialProfileTool(service=profile_service))
    registry.register(UpdateFinancialProfileTool(service=profile_service))

    executor = ToolExecutor(registry=registry, policy=ToolPolicy())

    context = RequestContext.create(
        user_id="user-001",
        session_id="session-001",
        operation="voice",
    )

    res_get = await executor.execute(
        tool_name="get_financial_profile",
        arguments={},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_get.success is True

    res_up = await executor.execute(
        tool_name="update_financial_profile",
        arguments={"monthly_income": 500000},
        context=context,
        state=QuantaState.IDLE,
    )
    assert res_up.success is True
    assert res_up.data["monthly_income"] == "500000.00"
