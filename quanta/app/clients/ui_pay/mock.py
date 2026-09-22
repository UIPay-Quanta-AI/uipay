from __future__ import annotations

from typing import Any

from app.clients.ui_pay.base import UIPayClient


class MockUIPayClient(UIPayClient):
    def __init__(
        self,
        *,
        beneficiaries: list[dict[str, Any]] | None = None,
    ) -> None:
        self._beneficiaries = beneficiaries or []

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
                normalized_query
                in beneficiary.get(
                    "nickname",
                    "",
                ).lower()
                or normalized_query
                in beneficiary.get(
                    "account_name",
                    "",
                ).lower()
            )
        ]
