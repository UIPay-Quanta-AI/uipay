from __future__ import annotations

from typing import Any, ClassVar

from app.clients.ui_pay.base import UIPayClient
from app.domain.financial_profile.models import (
    FinancialProfile,
    FinancialProfileDomainError,
)


class FinancialProfileServiceError(Exception):
    """Application level service error for financial profiles."""


class FinancialProfileService:
    """
    Application service managing financial profile operations.
    Integrates domain rules and UI Pay client data.
    """

    ALLOWED_UPDATE_FIELDS: ClassVar[set[str]] = {
        "monthly_income",
        "income_frequency",
        "employment_type",
        "fixed_expenses",
        "variable_expenses",
        "savings_target",
    }

    def __init__(self, *, client: UIPayClient) -> None:
        self._client = client

    async def get_profile(self, *, user_id: str) -> FinancialProfile:
        """Fetch and validate financial profile for the given user."""
        if not user_id or not user_id.strip():
            raise FinancialProfileServiceError("User identity context is required.")

        try:
            raw_data = await self._client.get_financial_profile(user_id=user_id.strip())
            profile = FinancialProfile.model_validate(raw_data)
            profile.validate_ownership(user_id.strip())
            return profile
        except FinancialProfileDomainError as exc:
            raise FinancialProfileServiceError(f"Invalid profile data: {exc}") from exc
        except Exception as exc:
            raise FinancialProfileServiceError(
                f"Failed to retrieve financial profile for user '{user_id}': {exc}"
            ) from exc

    async def update_profile(
        self,
        *,
        user_id: str,
        updates: dict[str, Any],
    ) -> tuple[FinancialProfile, list[str]]:
        """Validate updates, apply them via UI Pay, and return domain profile."""
        if not user_id or not user_id.strip():
            raise FinancialProfileServiceError("User identity context is required.")

        filtered_updates = {
            key: val
            for key, val in updates.items()
            if key in self.ALLOWED_UPDATE_FIELDS and val is not None
        }

        if not filtered_updates:
            raise FinancialProfileServiceError("No valid profile fields provided for update.")

        try:
            raw_data = await self._client.update_financial_profile(
                user_id=user_id.strip(),
                updates=filtered_updates,
            )
            profile = FinancialProfile.model_validate(raw_data)
            profile.validate_ownership(user_id.strip())
            return profile, list(filtered_updates.keys())
        except FinancialProfileDomainError as exc:
            raise FinancialProfileServiceError(f"Profile domain validation failed: {exc}") from exc
        except Exception as exc:
            raise FinancialProfileServiceError(
                f"Failed to update financial profile for user '{user_id}': {exc}"
            ) from exc
