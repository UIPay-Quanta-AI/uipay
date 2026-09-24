from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class RequestContext:
    """
    Trusted context for a single Quanta operation.

    The context carries request-scoped identity and metadata through
    the orchestration and tool execution layers.

    Sensitive authentication secrets such as passwords, PINs, API keys,
    access tokens, and raw credentials must never be stored here.
    """

    request_id: UUID
    user_id: str
    session_id: str
    operation: str
    locale: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        session_id: str,
        operation: str,
        locale: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RequestContext:
        """
        Create a new request context with a generated request ID.
        """

        if not user_id.strip():
            raise ValueError("user_id cannot be empty")

        if not session_id.strip():
            raise ValueError("session_id cannot be empty")

        if not operation.strip():
            raise ValueError("operation cannot be empty")

        return cls(
            request_id=uuid4(),
            user_id=user_id,
            session_id=session_id,
            operation=operation,
            locale=locale,
            metadata=dict(metadata or {}),
        )

    def to_log_dict(self) -> dict[str, Any]:
        """
        Return only non-sensitive fields suitable for structured logging.
        """

        return {
            "request_id": str(self.request_id),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "operation": self.operation,
            "locale": self.locale,
        }
