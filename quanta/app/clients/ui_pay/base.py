from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any


class UIPayClientError(Exception):
    """Base exception for UI Pay client failures."""


class UIPayClient(ABC):
    """
    Abstract interface to the UI Pay backend.

    Quanta tools depend on this interface rather than raw HTTP.
    """

    @abstractmethod
    async def search_beneficiaries(
        self,
        *,
        user_id: str,
        query: str,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_financial_profile(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def update_financial_profile(
        self,
        *,
        user_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def create_goal(
        self,
        *,
        user_id: str,
        goal_data: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_goals(
        self,
        *,
        user_id: str,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_goal(
        self,
        *,
        user_id: str,
        goal_id: str,
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def update_goal(
        self,
        *,
        user_id: str,
        goal_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def save_budget(
        self,
        *,
        user_id: str,
        budget_data: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_current_budget(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def get_budget_history(
        self,
        *,
        user_id: str,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_transactions(
        self,
        *,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_transaction_budget_context(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError
