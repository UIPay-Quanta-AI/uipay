"""
Structured Observability, Redaction, and Error Taxonomy for Quanta AI Microservice.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from app.core.context import RequestContext

logger = logging.getLogger("quanta.observability")


class ErrorTaxonomy(str, Enum):
    """
    Standardized error taxonomy distinguishing internal provider, domain, security,
    and validation failures.
    """

    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    WORKFLOW_ERROR = "workflow_error"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT_ERROR = "timeout_error"
    DOMAIN_ERROR = "domain_error"
    UNEXPECTED_ERROR = "unexpected_error"


# Keys that must NEVER be logged or leaked into structured trace context
SENSITIVE_KEYS: set[str] = {
    "pin",
    "password",
    "secret",
    "authorization",
    "token",
    "access_token",
    "api_key",
    "audio",
    "voice_profile",
    "raw_audio",
    "profile_bytes",
    "bvn",
    "account_credentials",
}


def redact_sensitive_data(val: Any) -> Any:
    """
    Recursively redact sensitive keys and raw biometric/audio byte payloads.
    """
    if isinstance(val, dict):
        redacted: dict[str, Any] = {}
        for k, v in val.items():
            k_lower = str(k).lower()
            if (
                k_lower in SENSITIVE_KEYS
                or "secret" in k_lower
                or "token" in k_lower
                or "pin" in k_lower
            ):
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = redact_sensitive_data(v)
        return redacted
    if isinstance(val, (bytes, bytearray)):
        return f"[BYTES payload len={len(val)}]"
    if isinstance(val, list):
        return [redact_sensitive_data(item) for item in val]
    return val


def log_request_event(
    event_name: str,
    context: RequestContext,
    *,
    status: str = "success",
    extra: dict[str, Any] | None = None,
) -> None:
    """Record a structured log event bound to trusted RequestContext correlation identifiers."""
    payload = {
        "event": event_name,
        "request_id": str(context.request_id),
        "user_id": context.user_id,
        "session_id": context.session_id,
        "operation": context.operation,
        "locale": context.locale,
        "status": status,
    }
    if extra:
        payload["details"] = redact_sensitive_data(extra)

    if status == "error":
        logger.error("REQUEST_EVENT: %s", payload)
    else:
        logger.info("REQUEST_EVENT: %s", payload)


def log_tool_execution(
    tool_name: str,
    context: RequestContext,
    *,
    success: bool,
    latency_ms: float | None = None,
    error: str | None = None,
) -> None:
    """Record tool execution outcome with correlation ID."""
    payload = {
        "event": "tool_execution",
        "tool_name": tool_name,
        "request_id": str(context.request_id),
        "user_id": context.user_id,
        "success": success,
        "latency_ms": latency_ms,
        "error": error,
    }
    if success:
        logger.info("TOOL_EXECUTION: %s", payload)
    else:
        logger.warning("TOOL_EXECUTION: %s", payload)


def log_security_decision(
    decision_type: str,
    context: RequestContext,
    *,
    allowed: bool,
    reason: str,
) -> None:
    """Record security or tool policy evaluation decision."""
    payload = {
        "event": "security_decision",
        "decision_type": decision_type,
        "request_id": str(context.request_id),
        "user_id": context.user_id,
        "allowed": allowed,
        "reason": reason,
    }
    if allowed:
        logger.info("SECURITY_DECISION: %s", payload)
    else:
        logger.warning("SECURITY_DECISION: %s", payload)
