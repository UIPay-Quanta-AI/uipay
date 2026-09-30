import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.context import RequestContext
from app.services.transaction_intelligence_service import TransactionIntelligenceService
from app.tools.base import Tool, ToolClassification, ToolResult

logger = logging.getLogger(__name__)


class GetTransactionInsightsInput(BaseModel):
    """
    Input schema for get_transaction_insights tool.
    NOTE: user_id is NOT permitted in arguments. Identity comes strictly from RequestContext.
    """

    model_config = ConfigDict(frozen=True)

    start_date: date | None = Field(
        default=None,
        description="Optional start date for transaction lookback (YYYY-MM-DD). Defaults to 365 days before end_date.",
    )
    end_date: date | None = Field(
        default=None,
        description="Optional end date for transaction lookback (YYYY-MM-DD). Defaults to today.",
    )


class GetTransactionInsightsOutput(BaseModel):
    """Output schema for get_transaction_insights tool."""

    model_config = ConfigDict(frozen=True)

    data_available: bool
    lookback_period: dict[str, str] | None = None
    trends: dict[str, Any] = Field(default_factory=dict)
    notable_changes: list[str] = Field(default_factory=list)
    financial_observations: list[dict[str, Any]] = Field(default_factory=list)
    budget_review_signals: list[dict[str, Any]] = Field(default_factory=list)
    income_totals: dict[str, Any] = Field(default_factory=dict)
    expense_totals: dict[str, Any] = Field(default_factory=dict)
    data_quality: dict[str, Any] = Field(default_factory=dict)
    sanitized_context: dict[str, Any] = Field(default_factory=dict)


class GetTransactionInsightsTool(Tool[GetTransactionInsightsInput, GetTransactionInsightsOutput]):
    """
    LLM-facing tool to retrieve transaction intelligence and financial insights.

    CLASSIFICATION: SENSITIVE_READ
    Security Boundaries:
    - User identity derived ONLY from RequestContext.user_id.
    - Raw transaction lists and operational references are excluded.
    - Does NOT mutate budgets or execute transfers.
    """

    name: str = "get_transaction_insights"
    description: str = (
        "Retrieve sanitized transaction intelligence insights including income/expense trends, "
        "recurring spending patterns, category breakdowns, financial observations, and budget review signals."
    )
    classification: ToolClassification = ToolClassification.SENSITIVE_READ
    input_model: type[GetTransactionInsightsInput] = GetTransactionInsightsInput
    output_model: type[GetTransactionInsightsOutput] = GetTransactionInsightsOutput

    def __init__(self, *, service: TransactionIntelligenceService) -> None:
        self._service = service

    async def execute(
        self,
        *,
        context: RequestContext,
        arguments: GetTransactionInsightsInput,
    ) -> ToolResult:
        try:
            today = datetime.now(UTC).date()
            end_date = arguments.end_date or today
            start_date = arguments.start_date or (end_date - timedelta(days=365))

            result = await self._service.analyze(
                context=context,
                start_date=start_date,
                end_date=end_date,
            )

            observations_dump = [
                obs.model_dump(mode="json") for obs in result.financial_observations
            ]

            sanitized_ctx = {
                "data_available": result.data_available,
                "lookback_period": result.lookback_period,
                "historical_periods": result.historical_periods,
                "trends": result.trends,
                "notable_changes": result.notable_changes,
                "financial_observations": observations_dump,
                "budget_review_signals": result.budget_review_signals,
                "data_quality": result.data_quality,
            }

            output = GetTransactionInsightsOutput(
                data_available=result.data_available,
                lookback_period=result.lookback_period,
                trends=result.trends,
                notable_changes=result.notable_changes,
                financial_observations=observations_dump,
                budget_review_signals=result.budget_review_signals,
                income_totals=result.income_totals,
                expense_totals=result.expense_totals,
                data_quality=result.data_quality,
                sanitized_context=sanitized_ctx,
            )

            return ToolResult(
                success=True,
                data=output.model_dump(mode="json"),
            )
        except Exception:
            logger.exception(
                "Transaction intelligence execution failed for request %s",
                context.request_id,
            )
            return ToolResult(
                success=False,
                error_code="TRANSACTION_INTELLIGENCE_ERROR",
                error_message="Unable to retrieve transaction insights right now.",
            )
