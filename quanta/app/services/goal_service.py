from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.clients.ui_pay.base import UIPayClient
from app.domain.goals.models import (
    FinancialGoal,
    GoalDomainError,
    GoalStatus,
)


class GoalServiceError(Exception):
    """Application level service error for financial goals."""


class GoalService:
    """
    Application service managing financial goal operations.
    Enforces domain invariants, user context security, and UI Pay data access.
    Goals are tracking objects and MUST NOT execute money movements.
    """

    def __init__(self, *, client: UIPayClient) -> None:
        self._client = client

    async def create_goal(
        self,
        *,
        user_id: str,
        name: str,
        target_amount: Decimal,
        target_date: date | None = None,
    ) -> FinancialGoal:
        """Create a new financial goal for the user."""
        if not user_id or not user_id.strip():
            raise GoalServiceError("User identity context is required.")

        if not name or not name.strip():
            raise GoalServiceError("Goal name cannot be empty.")

        if target_amount <= Decimal("0.00"):
            raise GoalServiceError("Target amount must be strictly greater than zero.")

        payload = {
            "name": name.strip(),
            "target_amount": str(target_amount),
            "current_amount": "0.00",
            "target_date": target_date.isoformat() if target_date else None,
            "currency": "NGN",
            "status": GoalStatus.ACTIVE.value,
        }

        try:
            raw_data = await self._client.create_goal(
                user_id=user_id.strip(),
                goal_data=payload,
            )
            goal = FinancialGoal.model_validate(raw_data)
            goal.validate_ownership(user_id.strip())
            return goal
        except GoalDomainError as exc:
            raise GoalServiceError(f"Goal domain rule violation: {exc}") from exc
        except Exception as exc:
            raise GoalServiceError(f"Failed to create goal for user '{user_id}': {exc}") from exc

    async def get_goals(
        self,
        *,
        user_id: str,
        status: GoalStatus | None = None,
    ) -> list[FinancialGoal]:
        """Retrieve financial goals for the user, optionally filtered by status."""
        if not user_id or not user_id.strip():
            raise GoalServiceError("User identity context is required.")

        try:
            raw_list = await self._client.get_goals(user_id=user_id.strip())
            goals: list[FinancialGoal] = []
            for item in raw_list:
                goal = FinancialGoal.model_validate(item)
                goal.validate_ownership(user_id.strip())
                if status is None or goal.status == status:
                    goals.append(goal)
            return goals
        except Exception as exc:
            raise GoalServiceError(f"Failed to retrieve goals for user '{user_id}': {exc}") from exc

    async def get_goal(
        self,
        *,
        user_id: str,
        goal_identifier: str,
    ) -> FinancialGoal:
        """Retrieve a specific financial goal by ID or name for the user."""
        if not user_id or not user_id.strip():
            raise GoalServiceError("User identity context is required.")

        if not goal_identifier or not goal_identifier.strip():
            raise GoalServiceError("Goal identifier cannot be empty.")

        try:
            raw_data = await self._client.get_goal(
                user_id=user_id.strip(),
                goal_id=goal_identifier.strip(),
            )
            if not raw_data:
                raise GoalServiceError(f"Goal '{goal_identifier}' not found for user '{user_id}'.")

            goal = FinancialGoal.model_validate(raw_data)
            goal.validate_ownership(user_id.strip())
            return goal
        except GoalServiceError:
            raise
        except Exception as exc:
            raise GoalServiceError(
                f"Error retrieving goal '{goal_identifier}' for user '{user_id}': {exc}"
            ) from exc

    async def update_goal(
        self,
        *,
        user_id: str,
        goal_identifier: str,
        updates: dict[str, Any],
    ) -> FinancialGoal:
        """Update an existing goal after validating domain lifecycle invariants."""
        existing_goal = await self.get_goal(user_id=user_id, goal_identifier=goal_identifier)

        new_current = updates.get("current_amount")
        if isinstance(new_current, (int, float, str)):
            new_current = Decimal(str(new_current))

        new_status = updates.get("status")
        if isinstance(new_status, str):
            new_status = GoalStatus(new_status)

        try:
            existing_goal.validate_update(
                new_current_amount=new_current,
                new_status=new_status,
            )
        except GoalDomainError as exc:
            raise GoalServiceError(f"Goal update prohibited: {exc}") from exc

        formatted_updates: dict[str, Any] = {}
        for key, val in updates.items():
            if val is not None:
                if isinstance(val, (Decimal, int, float)):
                    formatted_updates[key] = str(val)
                elif isinstance(val, date):
                    formatted_updates[key] = val.isoformat()
                elif isinstance(val, GoalStatus):
                    formatted_updates[key] = val.value
                else:
                    formatted_updates[key] = val

        try:
            raw_data = await self._client.update_goal(
                user_id=user_id.strip(),
                goal_id=existing_goal.id,
                updates=formatted_updates,
            )
            updated_goal = FinancialGoal.model_validate(raw_data)
            updated_goal.validate_ownership(user_id.strip())
            return updated_goal
        except GoalDomainError as exc:
            raise GoalServiceError(f"Updated goal violates domain rules: {exc}") from exc
        except Exception as exc:
            raise GoalServiceError(
                f"Failed to update goal '{goal_identifier}' for user '{user_id}': {exc}"
            ) from exc
