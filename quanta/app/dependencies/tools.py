from __future__ import annotations

from app.clients.ui_pay.base import UIPayClient
from app.tools.implementations.beneficiary import SearchBeneficiaryTool
from app.tools.registry import ToolRegistry


def build_tool_registry(
    *,
    ui_pay_client: UIPayClient,
) -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        SearchBeneficiaryTool(
            client=ui_pay_client,
        )
    )

    return registry
