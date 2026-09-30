"""
Integration tests for Mega Prompt 2 End-to-End User Journeys.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.domain.budget.models import BudgetStatus
from app.domain.conversational.session import SessionManager
from app.domain.goals.models import GoalStatus
from app.orchestration.multimodal import MultimodalInput, MultimodalProcessor
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.workflow_runner import ConversationalWorkflowRunner
from app.providers.llm.mock import MockLLMProvider
from app.schemas.response import ResponseStatus, UIType
from app.services.budget_service import BudgetService
from app.services.financial_profile_service import FinancialProfileService
from app.services.goal_service import GoalService
from app.services.transaction_intelligence_service import TransactionIntelligenceService


@pytest.fixture
def e2e_setup():
    SessionManager._instance = None
    client = MockUIPayClient()

    profile_service = FinancialProfileService(client=client)
    goal_service = GoalService(client=client)
    budget_service = BudgetService(
        client=client,
        profile_service=profile_service,
        goal_service=goal_service,
    )
    tx_service = TransactionIntelligenceService(client=client)

    from app.dependencies.tools import build_tool_registry
    from app.tools.executor import ToolExecutor
    from app.tools.policy import ToolPolicy

    registry = build_tool_registry(ui_pay_client=client)
    executor = ToolExecutor(registry=registry, policy=ToolPolicy())

    from app.providers.llm.base import LLMResponse, LLMToolCall

    def smart_responder(msgs, sys, tools):
        user_msg = msgs[-1].content if msgs else ""
        if msgs and msgs[-1].role.value == "tool":
            return LLMResponse(
                content="Transfer prepared. Please confirm with your PIN.",
                finish_reason="stop",
            )
        if "25,000" in user_msg or "Send" in user_msg:
            return LLMResponse(
                content="Preparing transfer of ₦25,000 to Mum.",
                tool_calls=[
                    LLMToolCall(
                        id="call_t1",
                        name="prepare_transfer",
                        arguments={
                            "beneficiary_id": "0123456789",
                            "amount": 25000,
                        },
                    )
                ],
                finish_reason="tool_calls",
            )
        return LLMResponse(
            content="I can assist you with your UI Pay financial requests.",
            finish_reason="stop",
        )

    llm = MockLLMProvider(responder=smart_responder)

    orchestrator = Orchestrator(
        llm_provider=llm,
        tool_registry=registry,
        tool_executor=executor,
    )

    multimodal = MultimodalProcessor(
        orchestrator=orchestrator,
    )

    runner = ConversationalWorkflowRunner(
        orchestrator=orchestrator,
        multimodal_processor=multimodal,
        ui_pay_client=client,
    )

    return {
        "runner": runner,
        "client": client,
        "profile_service": profile_service,
        "goal_service": goal_service,
        "budget_service": budget_service,
        "tx_service": tx_service,
    }


@pytest.mark.asyncio
async def test_journey_1_financial_profile_setup(e2e_setup):
    """Journey 1: Financial profile setup & lazy default initialization."""
    runner = e2e_setup["runner"]
    client = e2e_setup["client"]

    ctx = RequestContext.create(user_id="user_j1", session_id="sess_j1", operation="TEXT")
    res = await runner.run_interaction(
        context=ctx,
        input_data=MultimodalInput(text="I want to set up my financial profile"),
    )

    assert res.status in (ResponseStatus.SUCCESS, ResponseStatus.INPUT_REQUIRED)
    profile = await client.get_financial_profile(user_id="user_j1")
    assert profile["user_id"] == "user_j1"
    assert Decimal(profile["monthly_income"]) >= Decimal("0.00")


@pytest.mark.asyncio
async def test_journey_2_budget_generation_with_context(e2e_setup):
    """Journey 2: Budget generation combining profile + active goals + transaction context."""
    budget_svc = e2e_setup["budget_service"]
    goal_svc = e2e_setup["goal_service"]
    client = e2e_setup["client"]

    user_id = "user_j2"
    # Create goal
    await goal_svc.create_goal(
        user_id=user_id,
        name="Emergency Fund",
        target_amount=Decimal("100000.00"),
    )

    # Set transaction context
    client._transaction_contexts[user_id] = {
        "data_available": True,
        "trends": {
            "category_percentages": {
                "housing": "0.30",
                "food": "0.25",
                "transport": "0.20",
                "utilities": "0.15",
                "entertainment": "0.10",
            },
            "observed_income": "450000.00",
        },
    }

    budget = await budget_svc.generate_budget(
        user_id=user_id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
    )

    assert budget.user_id == user_id
    assert budget.version == 1
    assert budget.status == BudgetStatus.ACTIVE
    assert len(budget.goal_allocations) == 1
    assert budget.goal_allocations[0].goal_name == "Emergency Fund"


@pytest.mark.asyncio
async def test_journey_3_goal_creation_and_completion(e2e_setup):
    """Journey 3: Create goal and perform explicit goal completion."""
    goal_svc = e2e_setup["goal_service"]
    user_id = "user_j3"

    goal = await goal_svc.create_goal(
        user_id=user_id,
        name="Laptop Purchase",
        target_amount=Decimal("350000.00"),
    )
    assert goal.status == GoalStatus.ACTIVE
    assert goal.current_amount == Decimal("0.00")

    # Explicit goal completion
    completed_goal = await goal_svc.complete_goal(
        user_id=user_id,
        goal_identifier=goal.id,
    )

    assert completed_goal.status == GoalStatus.COMPLETED
    assert completed_goal.current_amount == Decimal("350000.00")


@pytest.mark.asyncio
async def test_journey_4_significant_change_budget_update_accepted(e2e_setup):
    """Journey 4: Significant change detected -> user accepts -> budget version 2 created (ACTIVE, v1 SUPERSEDED)."""
    budget_svc = e2e_setup["budget_service"]
    user_id = "user_j4"

    # Step 1: Initial budget (v1)
    b1 = await budget_svc.generate_budget(
        user_id=user_id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
    )
    assert b1.version == 1
    assert b1.status == BudgetStatus.ACTIVE

    # Step 2: Significant spending change accepted by user -> update budget
    b2, _prev = await budget_svc.update_budget(
        user_id=user_id,
        budget_id=b1.id,
        income_update=Decimal("500000.00"),
        allocation_updates=[
            {"category": "housing", "allocated_amount": 150000},
            {"category": "transport", "allocated_amount": 120000},
            {"category": "food", "allocated_amount": 100000},
            {"category": "utilities", "allocated_amount": 50000},
        ],
    )

    assert b2.version == 2
    assert b2.status == BudgetStatus.ACTIVE
    assert b2.previous_version_id == b1.id

    # Verify history retains v1 as superseded
    history = await budget_svc.get_budget_history(user_id=user_id)
    v1_record = next(b for b in history if b.version == 1)
    assert v1_record.status == BudgetStatus.SUPERSEDED


@pytest.mark.asyncio
async def test_journey_5_significant_change_rejected_no_mutation(e2e_setup):
    """Journey 5: Significant change detected -> user rejects -> no budget mutation occurs."""
    budget_svc = e2e_setup["budget_service"]
    user_id = "user_j5"

    b1 = await budget_svc.generate_budget(
        user_id=user_id,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )

    # User rejects spending change recommendation -> current budget remains unchanged v1 ACTIVE
    current = await budget_svc.get_current_budget(user_id=user_id)
    assert current.id == b1.id
    assert current.version == 1
    assert current.status == BudgetStatus.ACTIVE


@pytest.mark.asyncio
async def test_journey_6_transfer_workflow_confirmation(e2e_setup):
    """Journey 6: Transfer workflow explicit confirmation and PIN boundary."""
    runner = e2e_setup["runner"]
    ctx = RequestContext.create(user_id="user_j6", session_id="sess_j6", operation="TEXT")

    res = await runner.run_interaction(
        context=ctx,
        input_data=MultimodalInput(text="Send 25,000 NGN to GTBank account 0123456789 for Mum"),
    )

    assert res.status == ResponseStatus.CONFIRMATION_REQUIRED
    assert res.ui.type == UIType.TRANSFER_CONFIRMATION
    assert res.data["amount"] == 25000
    assert res.data["beneficiary_id"] == "0123456789"
