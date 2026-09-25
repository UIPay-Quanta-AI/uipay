from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from app.domain.confirmation.models import Confirmation, ConfirmationStatus


class ConfirmationStore(ABC):
    """
    Abstract persistence interface for confirmation records.

    Allows swapping the prototype's in-memory storage with durable storage (e.g. Redis)
    without modifying domain logic.
    """

    @abstractmethod
    async def create(self, confirmation: Confirmation) -> Confirmation:
        """Store a new confirmation record."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, confirmation_id: str) -> Confirmation | None:
        """Retrieve a confirmation record by ID."""
        raise NotImplementedError

    @abstractmethod
    async def update(self, confirmation: Confirmation) -> Confirmation:
        """Update an existing confirmation record."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, confirmation_id: str) -> None:
        """Delete a confirmation record by ID."""
        raise NotImplementedError

    @abstractmethod
    async def find_latest_pending(
        self,
        user_id: str,
        session_id: str,
    ) -> Confirmation | None:
        """Find the active pending confirmation for a given user and session."""
        raise NotImplementedError


class InMemoryConfirmationStore(ConfirmationStore):
    """
    In-memory confirmation store for development and testing.

    Thread-safe and async-aware using an internal lock.
    """

    def __init__(self) -> None:
        self._store: dict[str, Confirmation] = {}
        self._lock = asyncio.Lock()

    async def create(self, confirmation: Confirmation) -> Confirmation:
        async with self._lock:
            self._store[confirmation.confirmation_id] = confirmation
            return confirmation

    async def get(self, confirmation_id: str) -> Confirmation | None:
        async with self._lock:
            return self._store.get(confirmation_id)

    async def update(self, confirmation: Confirmation) -> Confirmation:
        async with self._lock:
            self._store[confirmation.confirmation_id] = confirmation
            return confirmation

    async def delete(self, confirmation_id: str) -> None:
        async with self._lock:
            self._store.pop(confirmation_id, None)

    async def find_latest_pending(
        self,
        user_id: str,
        session_id: str,
    ) -> Confirmation | None:
        async with self._lock:
            pending_records = [
                conf
                for conf in self._store.values()
                if conf.user_id == user_id
                and conf.session_id == session_id
                and conf.status == ConfirmationStatus.PENDING
            ]
            if not pending_records:
                return None
            pending_records.sort(key=lambda c: c.created_at, reverse=True)
            return pending_records[0]
