from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.clients.ui_pay.base import UIPayClient, UIPayClientError


class MockUIPayClient(UIPayClient):
    def __init__(
        self,
        *,
        beneficiaries: list[dict[str, Any]] | None = None,
        profiles: dict[str, dict[str, Any]] | None = None,
        goals: dict[str, list[dict[str, Any]]] | None = None,
        budgets: dict[str, list[dict[str, Any]]] | None = None,
        transaction_contexts: dict[str, dict[str, Any]] | None = None,
        transactions: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self._beneficiaries = beneficiaries or []
        self._profiles = profiles or {}
        self._goals = goals or {}
        self._budgets = budgets or {}
        self._transaction_contexts = transaction_contexts or {}
        self._transactions = transactions or {}

    async def search_beneficiaries(
        self,
        *,
        user_id: str,
        query: str,
    ) -> list[dict[str, Any]]:
        normalized_query = query.strip().lower()

        return [
            beneficiary
            for beneficiary in self._beneficiaries
            if beneficiary["user_id"] == user_id
            and (
                normalized_query in beneficiary.get("nickname", "").lower()
                or normalized_query in beneficiary.get("account_name", "").lower()
                or normalized_query in beneficiary.get("account_number", "").lower()
            )
        ]

    async def get_financial_profile(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any]:
        if user_id not in self._profiles:
            # Default demo financial profile for user
            now = datetime.now(UTC).isoformat()
            self._profiles[user_id] = {
                "user_id": user_id,
                "monthly_income": "300000.00",
                "income_frequency": "monthly",
                "employment_type": "salaried",
                "fixed_expenses": "120000.00",
                "variable_expenses": "80000.00",
                "savings_target": "50000.00",
                "currency": "NGN",
                "created_at": now,
                "updated_at": now,
            }
        return dict(self._profiles[user_id])

    async def get_or_initialize_financial_profile(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any]:
        return await self.get_financial_profile(user_id=user_id)

    async def update_financial_profile(
        self,
        *,
        user_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        profile = await self.get_financial_profile(user_id=user_id)
        monetary_fields = {
            "monthly_income",
            "fixed_expenses",
            "variable_expenses",
            "savings_target",
        }
        for key, value in updates.items():
            if value is not None:
                if key in monetary_fields:
                    profile[key] = f"{Decimal(str(value)):.2f}"
                else:
                    profile[key] = str(value) if isinstance(value, (int, float, Decimal)) else value
        profile["updated_at"] = datetime.now(UTC).isoformat()
        self._profiles[user_id] = profile
        return dict(profile)

    async def create_goal(
        self,
        *,
        user_id: str,
        goal_data: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        goal_id = goal_data.get("id") or f"goal-{uuid4().hex[:8]}"
        goal = {
            "id": goal_id,
            "user_id": user_id,
            "name": goal_data["name"],
            "target_amount": f"{Decimal(str(goal_data['target_amount'])):.2f}",
            "current_amount": f"{Decimal(str(goal_data.get('current_amount', '0.00'))):.2f}",
            "target_date": goal_data.get("target_date"),
            "currency": goal_data.get("currency", "NGN"),
            "status": goal_data.get("status", "active"),
            "created_at": now,
            "updated_at": now,
        }
        if user_id not in self._goals:
            self._goals[user_id] = []
        self._goals[user_id].append(goal)
        return dict(goal)

    async def get_goals(
        self,
        *,
        user_id: str,
    ) -> list[dict[str, Any]]:
        return [dict(g) for g in self._goals.get(user_id, [])]

    async def get_goal(
        self,
        *,
        user_id: str,
        goal_id: str,
    ) -> dict[str, Any] | None:
        user_goals = self._goals.get(user_id, [])
        for g in user_goals:
            if g["id"] == goal_id or g["name"].lower() == goal_id.lower():
                return dict(g)
        return None

    async def update_goal(
        self,
        *,
        user_id: str,
        goal_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        user_goals = self._goals.get(user_id, [])
        target_goal = None
        for g in user_goals:
            if g["id"] == goal_id or g["name"].lower() == goal_id.lower():
                target_goal = g
                break

        if not target_goal:
            raise UIPayClientError(f"Goal not found: {goal_id}")

        monetary_fields = {"target_amount", "current_amount"}
        for key, val in updates.items():
            if val is not None:
                if key in monetary_fields:
                    target_goal[key] = f"{Decimal(str(val)):.2f}"
                else:
                    target_goal[key] = str(val) if isinstance(val, (int, float, Decimal)) else val
        target_goal["updated_at"] = datetime.now(UTC).isoformat()
        return dict(target_goal)

    async def save_budget(
        self,
        *,
        user_id: str,
        budget_data: dict[str, Any],
    ) -> dict[str, Any]:
        if user_id not in self._budgets:
            self._budgets[user_id] = []

        # If previous version exists and is active, set status to superseded
        for b in self._budgets[user_id]:
            if b.get("status") == "active":
                b["status"] = "superseded"

        saved_budget = dict(budget_data)
        self._budgets[user_id].append(saved_budget)
        return dict(saved_budget)

    async def get_current_budget(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any] | None:
        user_budgets = self._budgets.get(user_id, [])
        active_budgets = [b for b in user_budgets if b.get("status") == "active"]
        if not active_budgets:
            return None
        # Return highest version active budget
        active_budgets.sort(key=lambda b: b.get("version", 1), reverse=True)
        return dict(active_budgets[0])

    async def get_budget_history(
        self,
        *,
        user_id: str,
    ) -> list[dict[str, Any]]:
        user_budgets = self._budgets.get(user_id, [])
        return [dict(b) for b in sorted(user_budgets, key=lambda b: b.get("version", 1))]

    async def get_transactions(
        self,
        *,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        user_txs = self._transactions.get(user_id, [])
        return [dict(tx) for tx in user_txs if self._tx_in_window(tx, start_date, end_date)]

    def _tx_in_window(self, tx: dict[str, Any], start_date: date, end_date: date) -> bool:
        date_value = tx.get("date")
        if isinstance(date_value, str):
            try:
                tx_date = date.fromisoformat(date_value)
            except ValueError:
                return True
        elif isinstance(date_value, date):
            tx_date = date_value
        else:
            return True
        return start_date <= tx_date <= end_date

    async def get_transaction_budget_context(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any]:
        if hasattr(self, "_transaction_contexts") and user_id in self._transaction_contexts:
            return dict(self._transaction_contexts[user_id])
        return {"data_available": False}
