from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.context import RequestContext
from app.domain.financial_profile.models import EmploymentType, IncomeFrequency
from app.services.financial_profile_service import FinancialProfileService
from app.tools.base import Tool, ToolClassification, ToolResult


class UpdateFinancialProfileInput(BaseModel):
    """Input for updating financial profile fields."""

    model_config = ConfigDict(frozen=True)

    monthly_income: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    income_frequency: IncomeFrequency | None = None
    employment_type: EmploymentType | None = None
    fixed_expenses: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    variable_expenses: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    savings_target: Decimal | None = Field(default=None, ge=Decimal("0.00"))


class UpdateFinancialProfileOutput(BaseModel):
    monthly_income: Decimal = Field(ge=Decimal("0.00"))
    income_frequency: str
    employment_type: str
    fixed_expenses: Decimal = Field(ge=Decimal("0.00"))
    variable_expenses: Decimal = Field(ge=Decimal("0.00"))
    savings_target: Decimal = Field(ge=Decimal("0.00"))
    currency: str = "NGN"
    updated_fields: list[str]


class UpdateFinancialProfileTool(Tool[UpdateFinancialProfileInput, UpdateFinancialProfileOutput]):
    name = "update_financial_profile"
    description = (
        "Update fields in the authenticated user's financial profile such as monthly income, "
        "income frequency, employment type, fixed expenses, variable expenses, or savings target."
    )
    classification = ToolClassification.WRITE
    input_model = UpdateFinancialProfileInput
    output_model = UpdateFinancialProfileOutput

    def __init__(self, *, service: FinancialProfileService) -> None:
        self._service = service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: UpdateFinancialProfileInput,
    ) -> ToolResult:
        updates = arguments.model_dump(exclude_unset=True)
        if not updates:
            return ToolResult(
                success=False,
                error_code="INVALID_ARGUMENTS",
                error_message="At least one profile field must be specified to update.",
            )

        try:
            profile, updated_fields = await self._service.update_profile(
                user_id=context.user_id,
                updates=updates,
            )
            output = UpdateFinancialProfileOutput(
                monthly_income=profile.monthly_income,
                income_frequency=profile.income_frequency.value,
                employment_type=profile.employment_type.value,
                fixed_expenses=profile.fixed_expenses,
                variable_expenses=profile.variable_expenses,
                savings_target=profile.savings_target,
                currency=profile.currency,
                updated_fields=updated_fields,
            )
            return ToolResult(
                success=True,
                data=output.model_dump(mode="json"),
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                error_code="FINANCIAL_PROFILE_UPDATE_FAILED",
                error_message=str(exc),
            )
