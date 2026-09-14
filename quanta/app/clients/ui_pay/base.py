from __future__ import annotations

from abc import ABC, abstractmethod
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
