from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

import httpx

from app.clients.ui_pay.base import (
    UIPayAuthError,
    UIPayClient,
    UIPayClientError,
    UIPayConnectionError,
    UIPayNotFoundError,
    UIPayServerError,
    UIPayTimeoutError,
    UIPayValidationError,
)

logger = logging.getLogger("quanta.clients.ui_pay")


class RealUIPayClient(UIPayClient):
    """
    Production-credible HTTP client adapter for the UI Pay backend.

    Domain services depend on the UIPayClient interface; this implementation
    handles HTTP transport, correlation ID propagation, safe non-retrying write policies,
    and singleton FinancialProfile initialization.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:8001",
        service_token: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token
        self.timeout = timeout
        self.max_retries = max_retries
        self._external_client = http_client

    def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=5.0),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        request_id: str | None = None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        is_retryable: bool = False,
    ) -> Any:
        headers = {"Content-Type": "application/json"}
        if self.service_token:
            headers["Authorization"] = f"Bearer {self.service_token}"
        if request_id:
            headers["X-Request-ID"] = request_id
            headers["X-Correlation-ID"] = request_id

        attempts = 0
        max_attempts = (self.max_retries + 1) if is_retryable else 1

        while attempts < max_attempts:
            attempts += 1
            try:
                if self._external_client is not None:
                    res = await self._external_client.request(
                        method=method,
                        url=path,
                        json=json_data,
                        params=params,
                        headers=headers,
                    )
                else:
                    async with httpx.AsyncClient(
                        base_url=self.base_url,
                        timeout=httpx.Timeout(self.timeout, connect=5.0),
                    ) as local_client:
                        res = await local_client.request(
                            method=method,
                            url=path,
                            json=json_data,
                            params=params,
                            headers=headers,
                        )

                if res.status_code >= 200 and res.status_code < 300:
                    if res.status_code == 204:
                        return None
                    return res.json()

                # Status Error Mapping
                if res.status_code in (401, 403):
                    raise UIPayAuthError(f"UI Pay auth error ({res.status_code}): {res.text}")
                if res.status_code == 404:
                    raise UIPayNotFoundError(f"UI Pay resource not found (404): {path}")
                if res.status_code in (400, 422):
                    raise UIPayValidationError(
                        f"UI Pay validation error ({res.status_code}): {res.text}"
                    )
                if res.status_code >= 500:
                    if is_retryable and attempts < max_attempts:
                        await asyncio.sleep(0.2 * (2 ** (attempts - 1)))
                        continue
                    raise UIPayServerError(f"UI Pay server error ({res.status_code}): {res.text}")

                raise UIPayClientError(
                    f"UI Pay unexpected HTTP status {res.status_code}: {res.text}"
                )

            except (httpx.TimeoutException, TimeoutError) as exc:
                if is_retryable and attempts < max_attempts:
                    await asyncio.sleep(0.2 * (2 ** (attempts - 1)))
                    continue
                raise UIPayTimeoutError(f"UI Pay request timed out: {path}") from exc

            except (httpx.NetworkError, httpx.ConnectError) as exc:
                if is_retryable and attempts < max_attempts:
                    await asyncio.sleep(0.2 * (2 ** (attempts - 1)))
                    continue
                raise UIPayConnectionError(f"UI Pay connection failed: {path}") from exc

            except UIPayClientError:
                raise
            except Exception as exc:
                raise UIPayClientError(f"UI Pay client error: {exc!s}") from exc

    async def search_beneficiaries(
        self,
        *,
        user_id: str,
        query: str,
    ) -> list[dict[str, Any]]:
        res = await self._request(
            "GET",
            f"/api/v1/users/{user_id}/beneficiaries",
            params={"query": query},
            is_retryable=True,
        )
        return res if isinstance(res, list) else res.get("items", [])

    async def get_financial_profile(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/api/v1/users/{user_id}/profile",
            is_retryable=True,
        )

    async def get_or_initialize_financial_profile(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Singleton profile retrieval with automatic initialization.
        Attempts GET; if 404, initializes singleton defaults via POST/upsert.
        """
        try:
            return await self.get_financial_profile(user_id=user_id)
        except UIPayNotFoundError:
            default_profile = {
                "user_id": user_id,
                "monthly_income": "0.00",
                "income_frequency": "monthly",
                "employment_type": "salaried",
                "fixed_expenses": "0.00",
                "variable_expenses": "0.00",
                "savings_target": "0.00",
                "currency": "NGN",
            }
            try:
                return await self._request(
                    "POST",
                    f"/api/v1/users/{user_id}/profile",
                    json_data=default_profile,
                    is_retryable=False,  # Financial write: no auto retry
                )
            except (UIPayValidationError, UIPayClientError):
                # If race condition occurred (409 Conflict / existing profile), retry GET once
                return await self.get_financial_profile(user_id=user_id)

    async def update_financial_profile(
        self,
        *,
        user_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/v1/users/{user_id}/profile",
            json_data=updates,
            is_retryable=False,
        )

    async def create_goal(
        self,
        *,
        user_id: str,
        goal_data: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/v1/users/{user_id}/goals",
            json_data=goal_data,
            is_retryable=False,
        )

    async def get_goals(
        self,
        *,
        user_id: str,
    ) -> list[dict[str, Any]]:
        res = await self._request(
            "GET",
            f"/api/v1/users/{user_id}/goals",
            is_retryable=True,
        )
        return res if isinstance(res, list) else res.get("items", [])

    async def get_goal(
        self,
        *,
        user_id: str,
        goal_id: str,
    ) -> dict[str, Any] | None:
        try:
            return await self._request(
                "GET",
                f"/api/v1/users/{user_id}/goals/{goal_id}",
                is_retryable=True,
            )
        except UIPayNotFoundError:
            return None

    async def update_goal(
        self,
        *,
        user_id: str,
        goal_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/v1/users/{user_id}/goals/{goal_id}",
            json_data=updates,
            is_retryable=False,
        )

    async def save_budget(
        self,
        *,
        user_id: str,
        budget_data: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/v1/users/{user_id}/budgets",
            json_data=budget_data,
            is_retryable=False,
        )

    async def get_current_budget(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any] | None:
        try:
            return await self._request(
                "GET",
                f"/api/v1/users/{user_id}/budgets/current",
                is_retryable=True,
            )
        except UIPayNotFoundError:
            return None

    async def get_budget_history(
        self,
        *,
        user_id: str,
    ) -> list[dict[str, Any]]:
        res = await self._request(
            "GET",
            f"/api/v1/users/{user_id}/budgets",
            is_retryable=True,
        )
        return res if isinstance(res, list) else res.get("items", [])

    async def get_transactions(
        self,
        *,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        res = await self._request(
            "GET",
            f"/api/v1/users/{user_id}/transactions",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            is_retryable=True,
        )
        return res if isinstance(res, list) else res.get("items", [])

    async def get_transaction_budget_context(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/api/v1/users/{user_id}/transaction-context",
            is_retryable=True,
        )
