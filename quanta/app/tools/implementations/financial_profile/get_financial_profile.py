from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.context import RequestContext
from app.services.financial_profile_service import FinancialProfileService
from app.tools.base import Tool, ToolClassification, ToolResult


class GetFinancialProfileInput(BaseModel):
    """Input for retrieving financial profile. User identity is derived from RequestContext."""

    model_config = ConfigDict(frozen=True)


class GetFinancialProfileOutput(BaseModel):
    monthly_income: Decimal = Field(ge=Decimal("0.00"))
    income_frequency: str
    employment_type: str
    fixed_expenses: Decimal = Field(ge=Decimal("0.00"))
    variable_expenses: Decimal = Field(ge=Decimal("0.00"))
    savings_target: Decimal = Field(ge=Decimal("0.00"))
    currency: str = "NGN"


class GetFinancialProfileTool(Tool[GetFinancialProfileInput, GetFinancialProfileOutput]):
    name = "get_financial_profile"
    description = (
        "Retrieve the authenticated user's financial profile, including income, "
        "employment type, fixed expenses, variable expenses, and savings target."
    )
    classification = ToolClassification.SENSITIVE_READ
    input_model = GetFinancialProfileInput
    output_model = GetFinancialProfileOutput

    def __init__(self, *, service: FinancialProfileService) -> None:
        self._service = service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: GetFinancialProfileInput,
    ) -> ToolResult:
        try:
            profile = await self._service.get_profile(user_id=context.user_id)
            output = GetFinancialProfileOutput(
                monthly_income=profile.monthly_income,
                income_frequency=profile.income_frequency.value,
                employment_type=profile.employment_type.value,
                fixed_expenses=profile.fixed_expenses,
                variable_expenses=profile.variable_expenses,
                savings_target=profile.savings_target,
                currency=profile.currency,
            )
            return ToolResult(
                success=True,
                data=output.model_dump(mode="json"),
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                error_code="FINANCIAL_PROFILE_GET_FAILED",
                error_message=str(exc),
            )
