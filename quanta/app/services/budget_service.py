from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, ClassVar
from uuid import uuid4

from app.clients.ui_pay.base import UIPayClient
from app.domain.budget.models import (
    Budget,
    BudgetAllocation,
    BudgetDomainError,
    BudgetStatus,
    GoalAllocation,
    IncomePlan,
    TransactionBudgetContext,
    UpdateReason,
)
from app.domain.goals.models import GoalStatus
from app.services.financial_profile_service import FinancialProfileService
from app.services.goal_service import GoalService


class BudgetServiceError(Exception):
    """Application level service error for budget operations."""


class BudgetService:
    """
    Application service managing deterministic budget generation, updating, and versioning.

    Key Invariants:
    1. Budgets are defined by explicit start_date and end_date. They are NOT inherently calendar monthly.
    2. Updating a budget does NOT restart the budget period; it creates a new version for the SAME start_date and end_date.
    3. Previous budget versions are preserved as immutable historical records.
    4. Calculations are deterministic; LLM natural language is never authoritative arithmetic.
    """

    DEFAULT_CATEGORY_PERCENTAGES: ClassVar[dict[str, Decimal]] = {
        "housing": Decimal("0.30"),
        "food": Decimal("0.25"),
        "transport": Decimal("0.15"),
        "utilities": Decimal("0.10"),
        "entertainment": Decimal("0.10"),
    }

    def __init__(
        self,
        *,
        client: UIPayClient,
        profile_service: FinancialProfileService,
        goal_service: GoalService,
    ) -> None:
        self._client = client
        self._profile_service = profile_service
        self._goal_service = goal_service

    async def generate_budget(
        self,
        *,
        user_id: str,
        start_date: date,
        end_date: date,
        income_override: Decimal | None = None,
        custom_allocations: list[dict[str, Any]] | None = None,
    ) -> Budget:
        """Generate a new budget for the given period based on Financial Profile, Goals, and optional Transaction Context."""
        if not user_id or not user_id.strip():
            raise BudgetServiceError("User identity context is required.")

        if start_date >= end_date:
            raise BudgetServiceError(
                f"Start date ({start_date}) must be before end date ({end_date})."
            )

        # 1. Fetch Financial Profile (authoritative planning input)
        profile = await self._profile_service.get_profile(user_id=user_id)
        expected_income = income_override if income_override is not None else profile.monthly_income

        if expected_income <= Decimal("0.00"):
            raise BudgetServiceError(
                "Expected income must be greater than zero to generate a budget."
            )

        # 2. Fetch Active Goals (planning input)
        active_goals = await self._goal_service.get_goals(user_id=user_id, status=GoalStatus.ACTIVE)

        # 3. Fetch optional Transaction Context
        raw_tx_context = await self._client.get_transaction_budget_context(user_id=user_id)
        tx_context = TransactionBudgetContext.model_validate(raw_tx_context)
        _has_tx_history = tx_context.data_available

        # 4. Calculate Goal Allocations
        goal_allocations: list[GoalAllocation] = []
        remaining_income_for_expenses = expected_income

        target_savings = min(profile.savings_target, expected_income)
        if active_goals and target_savings > Decimal("0.00"):
            per_goal_share = (target_savings / Decimal(len(active_goals))).quantize(Decimal("0.01"))
            for g in active_goals:
                alloc = min(per_goal_share, g.remaining_amount)
                if alloc > Decimal("0.00"):
                    goal_allocations.append(
                        GoalAllocation(
                            goal_id=g.id,
                            goal_name=g.name,
                            allocated_amount=alloc,
                        )
                    )
            total_goals_alloc = sum(
                (ga.allocated_amount for ga in goal_allocations), Decimal("0.00")
            )
            remaining_income_for_expenses -= total_goals_alloc

        # 5. Calculate Category Allocations
        allocations: list[BudgetAllocation] = []
        if custom_allocations:
            for item in custom_allocations:
                allocations.append(
                    BudgetAllocation(
                        category=item["category"],
                        allocated_amount=Decimal(str(item["allocated_amount"])),
                        notes=item.get("notes"),
                    )
                )
        else:
            # Use transaction history trends if available, otherwise default ratios
            cat_percentages = dict(self.DEFAULT_CATEGORY_PERCENTAGES)
            if _has_tx_history and tx_context.trends:
                hist_pcts = (
                    tx_context.trends.get("category_percentages") or tx_context.category_trends
                )
                if isinstance(hist_pcts, dict) and hist_pcts:
                    parsed_pcts: dict[str, Decimal] = {}
                    pct_sum = Decimal("0.00")
                    for cat, val in hist_pcts.items():
                        try:
                            d_val = Decimal(str(val))
                            if d_val > 0:
                                parsed_pcts[cat.lower()] = d_val
                                pct_sum += d_val
                        except Exception:  # noqa: BLE001, S110
                            pass
                    if pct_sum > 0:
                        cat_percentages = {c: (v / pct_sum) for c, v in parsed_pcts.items()}

            allocated_sum = Decimal("0.00")
            for cat, pct in cat_percentages.items():
                cat_amount = (remaining_income_for_expenses * pct).quantize(Decimal("0.01"))
                allocations.append(
                    BudgetAllocation(
                        category=cat,
                        allocated_amount=cat_amount,
                    )
                )
                allocated_sum += cat_amount

            # Remaining unallocated goes to miscellaneous category
            misc_amount = max(Decimal("0.00"), remaining_income_for_expenses - allocated_sum)
            if misc_amount > Decimal("0.00"):
                allocations.append(
                    BudgetAllocation(
                        category="miscellaneous",
                        allocated_amount=misc_amount,
                    )
                )

        income_plan = IncomePlan(
            expected_income=expected_income,
            income_sources=["monthly_income"],
        )

        budget_id = f"budget-{uuid4().hex[:8]}"
        budget = Budget(
            id=budget_id,
            user_id=user_id.strip(),
            start_date=start_date,
            end_date=end_date,
            currency="NGN",
            version=1,
            status=BudgetStatus.ACTIVE,
            income_plan=income_plan,
            allocations=allocations,
            goal_allocations=goal_allocations,
            update_reason=UpdateReason.INITIAL_GENERATION,
        )

        try:
            raw_saved = await self._client.save_budget(
                user_id=user_id.strip(),
                budget_data=budget.model_dump(mode="json"),
            )
            return Budget.model_validate(raw_saved)
        except BudgetDomainError as exc:
            raise BudgetServiceError(f"Generated budget violates domain rules: {exc}") from exc
        except Exception as exc:
            raise BudgetServiceError(f"Failed to save generated budget: {exc}") from exc

    async def update_budget(
        self,
        *,
        user_id: str,
        budget_id: str,
        as_of_date: date | None = None,
        income_update: Decimal | None = None,
        allocation_updates: list[dict[str, Any]] | None = None,
        goal_updates: list[dict[str, Any]] | None = None,
        update_reason: UpdateReason = UpdateReason.OTHER,
    ) -> tuple[Budget, Budget]:
        """
        Update an existing active budget by creating a new version.
        PRESERVES original start_date and end_date. Does NOT restart the budget period.
        """
        if not user_id or not user_id.strip():
            raise BudgetServiceError("User identity context is required.")

        current_budget = await self.get_current_budget(user_id=user_id)
        if not current_budget:
            raise BudgetServiceError(f"No active budget found for user '{user_id}'.")

        if current_budget.id != budget_id and budget_id.strip() != "":
            # Search history if budget_id differs
            history = await self.get_budget_history(user_id=user_id)
            match = next((b for b in history if b.id == budget_id), None)
            if match:
                current_budget = match
            else:
                raise BudgetServiceError(f"Budget '{budget_id}' not found for user '{user_id}'.")

        current_budget.validate_ownership(user_id.strip())

        # Determine remaining period without restarting period
        ref_date = as_of_date or datetime.now(UTC).date()
        # Ensure remaining_period does not crash if ref_date is within period
        if ref_date <= current_budget.end_date:
            _rem_start, _rem_end = current_budget.remaining_period(ref_date)

        # Recalculate income plan
        new_income = (
            income_update
            if income_update is not None
            else current_budget.income_plan.expected_income
        )
        new_income_plan = IncomePlan(
            expected_income=new_income,
            income_sources=current_budget.income_plan.income_sources,
        )

        # Recalculate allocations
        new_allocations: list[BudgetAllocation] = []
        if allocation_updates is not None:
            for item in allocation_updates:
                new_allocations.append(
                    BudgetAllocation(
                        category=item["category"],
                        allocated_amount=Decimal(str(item["allocated_amount"])),
                        notes=item.get("notes"),
                    )
                )
        else:
            new_allocations = list(current_budget.allocations)

        new_goal_allocations: list[GoalAllocation] = []
        if goal_updates is not None:
            for item in goal_updates:
                new_goal_allocations.append(
                    GoalAllocation(
                        goal_id=item["goal_id"],
                        goal_name=item["goal_name"],
                        allocated_amount=Decimal(str(item["allocated_amount"])),
                    )
                )
        else:
            new_goal_allocations = list(current_budget.goal_allocations)

        new_id = f"budget-{uuid4().hex[:8]}"
        new_version_budget = Budget(
            id=new_id,
            user_id=user_id.strip(),
            start_date=current_budget.start_date,  # PRESERVED ORIGINAL START DATE!
            end_date=current_budget.end_date,  # PRESERVED ORIGINAL END DATE!
            currency=current_budget.currency,
            version=current_budget.version + 1,
            status=BudgetStatus.ACTIVE,
            income_plan=new_income_plan,
            allocations=new_allocations,
            goal_allocations=new_goal_allocations,
            previous_version_id=current_budget.id,
            update_reason=update_reason,
        )

        try:
            raw_saved = await self._client.save_budget(
                user_id=user_id.strip(),
                budget_data=new_version_budget.model_dump(mode="json"),
            )
            saved_new_budget = Budget.model_validate(raw_saved)
            return saved_new_budget, current_budget
        except BudgetDomainError as exc:
            raise BudgetServiceError(f"Updated budget violates domain rules: {exc}") from exc
        except Exception as exc:
            raise BudgetServiceError(f"Failed to save budget update: {exc}") from exc

    async def get_current_budget(self, *, user_id: str) -> Budget | None:
        """Retrieve current active budget for user."""
        if not user_id or not user_id.strip():
            raise BudgetServiceError("User identity context is required.")

        try:
            raw_data = await self._client.get_current_budget(user_id=user_id.strip())
            if not raw_data:
                return None
            budget = Budget.model_validate(raw_data)
            budget.validate_ownership(user_id.strip())
            return budget
        except Exception as exc:
            raise BudgetServiceError(
                f"Failed to retrieve current budget for user '{user_id}': {exc}"
            ) from exc

    async def get_budget_history(self, *, user_id: str) -> list[Budget]:
        """Retrieve full version history of budgets for user."""
        if not user_id or not user_id.strip():
            raise BudgetServiceError("User identity context is required.")

        try:
            raw_history = await self._client.get_budget_history(user_id=user_id.strip())
            budgets: list[Budget] = []
            for item in raw_history:
                budget = Budget.model_validate(item)
                budget.validate_ownership(user_id.strip())
                budgets.append(budget)
            return budgets
        except Exception as exc:
            raise BudgetServiceError(
                f"Failed to retrieve budget history for user '{user_id}': {exc}"
            ) from exc
