from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from app.domain.state.models import QuantaState
from app.domain.state.transitions import ALLOWED_STATE_TRANSITIONS, InvalidStateTransitionError


@dataclass
class StateMachine:
    """
    Deterministic state machine for Quanta operations.

    The state machine is responsible only for validating and applying
    lifecycle transitions. Business operations remain outside this class.
    """

    current_state: QuantaState = QuantaState.IDLE

    _ALLOWED_TRANSITIONS: ClassVar[dict[QuantaState, frozenset[QuantaState]]] = (
        ALLOWED_STATE_TRANSITIONS
    )

    def can_transition(self, target_state: QuantaState) -> bool:
        """
        Return whether the current state can transition to target_state.
        """
        return target_state in self._ALLOWED_TRANSITIONS[self.current_state]

    def transition(self, target_state: QuantaState) -> QuantaState:
        """
        Validate and apply a state transition.

        Raises:
            InvalidStateTransitionError:
                If the requested transition is not allowed.
        """
        if not self.can_transition(target_state):
            raise InvalidStateTransitionError(
                current_state=self.current_state,
                requested_state=target_state,
            )

        self.current_state = target_state
        return self.current_state

    def reset(self) -> QuantaState:
        """
        Return the state machine to IDLE from a recoverable terminal state.

        SUCCESS is intentionally terminal and cannot be reset.
        """
        if self.current_state == QuantaState.IDLE:
            return self.current_state

        if self.current_state in {
            QuantaState.ERROR,
            QuantaState.CANCELLED,
            QuantaState.EXPIRED,
        }:
            return self.transition(QuantaState.IDLE)

        raise InvalidStateTransitionError(
            current_state=self.current_state,
            requested_state=QuantaState.IDLE,
        )


ApplicationStateManager = StateMachine
