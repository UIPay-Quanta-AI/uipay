from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar

from app.domain.conversational.requirements import QuestionRequirement
from app.providers.llm.base import LLMMessage


@dataclass
class SessionState:
    """
    In-memory representation of active conversational workflow context per session.
    """

    session_id: str
    user_id: str
    active_workflow: str | None = (
        None  # e.g., "FINANCIAL_PROFILE_SETUP", "BUDGET_SETUP", "TRANSFER", "SIGNIFICANT_CHANGE_BUDGET_UPDATE"
    )
    collected_data: dict[str, Any] = field(default_factory=dict)
    confirmed_profile_fields: set[str] = field(default_factory=set)
    pending_question: QuestionRequirement | None = None
    messages: list[LLMMessage] = field(default_factory=list)
    last_transfer_candidate: dict[str, Any] | None = None
    last_ti_observation: dict[str, Any] | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def update_timestamp(self) -> None:
        self.updated_at = datetime.now(UTC)

    def reset_workflow(self) -> None:
        self.active_workflow = None
        self.collected_data.clear()
        self.pending_question = None
        self.update_timestamp()


class SessionManager:
    """
    Thread-safe session state registry for active multi-turn workflows.
    """

    _instance: ClassVar[SessionManager | None] = None

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    @classmethod
    def get_instance(cls) -> SessionManager:
        if cls._instance is None:
            cls._instance = SessionManager()
        return cls._instance

    def get_session(self, *, session_id: str, user_id: str) -> SessionState:
        """
        Retrieve or initialize a SessionState for a session_id and user_id.
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(
                session_id=session_id,
                user_id=user_id,
            )
        session = self._sessions[session_id]
        # Re-verify user_id match
        if session.user_id != user_id:
            # Overwrite or re-initialize if user identity changed for session
            session = SessionState(
                session_id=session_id,
                user_id=user_id,
            )
            self._sessions[session_id] = session
        return session

    def clear_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]
