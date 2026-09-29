from __future__ import annotations

from app.clients.ui_pay.base import UIPayClient
from app.services.budget_service import BudgetService
from app.services.financial_profile_service import FinancialProfileService
from app.services.goal_service import GoalService
from app.services.transaction_intelligence_service import TransactionIntelligenceService
from app.tools.implementations.beneficiaries.beneficiary import SearchBeneficiaryTool
from app.tools.implementations.budget import (
    GenerateBudgetTool,
    GetBudgetHistoryTool,
    GetCurrentBudgetTool,
    UpdateBudgetTool,
)
from app.tools.implementations.financial_profile import (
    GetFinancialProfileTool,
    UpdateFinancialProfileTool,
)
from app.tools.implementations.goals import (
    CreateGoalTool,
    GetGoalsTool,
    GetGoalTool,
    UpdateGoalTool,
)
from app.tools.implementations.transaction_intelligence import GetTransactionInsightsTool
from app.tools.implementations.transfer import PrepareTransferTool
from app.tools.registry import ToolRegistry


def build_tool_registry(
    *,
    ui_pay_client: UIPayClient,
) -> ToolRegistry:
    registry = ToolRegistry()

    profile_service = FinancialProfileService(client=ui_pay_client)
    goal_service = GoalService(client=ui_pay_client)
    budget_service = BudgetService(
        client=ui_pay_client,
        profile_service=profile_service,
        goal_service=goal_service,
    )
    tx_intelligence_service = TransactionIntelligenceService(client=ui_pay_client)

    registry.register(
        SearchBeneficiaryTool(
            client=ui_pay_client,
        )
    )
    registry.register(PrepareTransferTool())
    registry.register(
        GetFinancialProfileTool(
            service=profile_service,
        )
    )
    registry.register(
        UpdateFinancialProfileTool(
            service=profile_service,
        )
    )
    registry.register(
        CreateGoalTool(
            service=goal_service,
        )
    )
    registry.register(
        GetGoalsTool(
            service=goal_service,
        )
    )
    registry.register(
        GetGoalTool(
            service=goal_service,
        )
    )
    registry.register(
        UpdateGoalTool(
            service=goal_service,
        )
    )
    registry.register(
        GenerateBudgetTool(
            service=budget_service,
        )
    )
    registry.register(
        UpdateBudgetTool(
            service=budget_service,
        )
    )
    registry.register(
        GetCurrentBudgetTool(
            service=budget_service,
        )
    )
    registry.register(
        GetBudgetHistoryTool(
            service=budget_service,
        )
    )
    registry.register(
        GetTransactionInsightsTool(
            service=tx_intelligence_service,
        )
    )

    return registry
