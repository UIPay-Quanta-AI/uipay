"""
System Prompt Builder for Quanta AI Agent.
"""

from __future__ import annotations

from typing import Any

from app.core.context import RequestContext
from app.prompts.budget_prompts import BUDGET_INSTRUCTIONS
from app.prompts.core_safety import CORE_SAFETY_INSTRUCTIONS
from app.prompts.financial_profile_prompts import FINANCIAL_PROFILE_INSTRUCTIONS
from app.prompts.goal_prompts import GOAL_INSTRUCTIONS
from app.prompts.language_prompts import LANGUAGE_INSTRUCTIONS
from app.prompts.transaction_intelligence_prompts import TRANSACTION_INTELLIGENCE_INSTRUCTIONS
from app.prompts.transfer_prompts import TRANSFER_INSTRUCTIONS


def build_quanta_system_prompt(
    context: RequestContext,
    active_workflow: str | None = None,
    session_data: dict[str, Any] | None = None,
) -> str:
    """
    Build a dynamic, modular system prompt based on RequestContext and active session workflow.
    """
    parts: list[str] = [
        "You are Quanta, the official AI financial agent for UI Pay.",
        f"Context: user_id='{context.user_id}', session_id='{context.session_id}', locale='{context.locale}'.",
        CORE_SAFETY_INSTRUCTIONS,
        FINANCIAL_PROFILE_INSTRUCTIONS,
        BUDGET_INSTRUCTIONS,
        GOAL_INSTRUCTIONS,
        TRANSACTION_INTELLIGENCE_INSTRUCTIONS,
        TRANSFER_INSTRUCTIONS,
        LANGUAGE_INSTRUCTIONS,
    ]

    if active_workflow:
        parts.append(f"\nCURRENT ACTIVE WORKFLOW: {active_workflow}")

    if session_data:
        parts.append(f"ACTIVE SESSION DATA: {session_data}")

    return "\n\n".join(parts)
