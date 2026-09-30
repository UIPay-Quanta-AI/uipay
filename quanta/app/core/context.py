from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

SUPPORTED_LOCALES: set[str] = {"en", "pcm", "ig", "yo", "ha"}

LOCALE_ALIASES: dict[str, str] = {
    "english": "en",
    "nigerian_english": "en",
    "nigerian english": "en",
    "en-ng": "en",
    "en_ng": "en",
    "pidgin": "pcm",
    "nigerian_pidgin": "pcm",
    "nigerian pidgin": "pcm",
    "pcm-ng": "pcm",
    "pcm_ng": "pcm",
    "igbo": "ig",
    "ig-ng": "ig",
    "ig_ng": "ig",
    "yoruba": "yo",
    "yo-ng": "yo",
    "yo_ng": "yo",
    "hausa": "ha",
    "ha-ng": "ha",
    "ha_ng": "ha",
}


def normalize_locale(locale: str | None) -> str:
    """
    Normalize requested locale to one of Quanta's canonical supported language codes:
    - 'en'  (Nigerian English)
    - 'pcm' (Nigerian Pidgin)
    - 'ig'  (Igbo)
    - 'yo'  (Yoruba)
    - 'ha'  (Hausa)

    Defaults to 'en' if locale is None, empty, or unrecognised.
    """
    if not locale or not locale.strip():
        return "en"
    cleaned = locale.strip().lower()
    if cleaned in SUPPORTED_LOCALES:
        return cleaned
    if cleaned in LOCALE_ALIASES:
        return LOCALE_ALIASES[cleaned]
    return "en"


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
    locale: str = "en"
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

        norm_locale = normalize_locale(locale)

        return cls(
            request_id=uuid4(),
            user_id=user_id,
            session_id=session_id,
            operation=operation,
            locale=norm_locale,
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
