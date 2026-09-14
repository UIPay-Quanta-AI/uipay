from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from app.schemas.states import QuantaState


class InvalidStateTransitionError(Exception):
    """
    Raised when an operation attempts an invalid state transition.
    """

    def __init__(
        self,
        *,
        current_state: QuantaState,
        requested_state: QuantaState,
    ) -> None:
        self.current_state = current_state
        self.requested_state = requested_state

        super().__init__(
            f"Invalid state transition: "
            f"{current_state.value} -> {requested_state.value}"
        )


@dataclass
class StateMachine:
    """
    Deterministic state machine for Quanta operations.

    The state machine is responsible only for validating and applying
    lifecycle transitions. Business operations remain outside this class.
    """

    current_state: QuantaState = QuantaState.IDLE

    _ALLOWED_TRANSITIONS: ClassVar[
        dict[QuantaState, frozenset[QuantaState]]
    ] = {
        QuantaState.IDLE: frozenset(
            {
                QuantaState.PROCESSING,
            }
        ),
        QuantaState.PROCESSING: frozenset(
            {
                QuantaState.AWAITING_INPUT,
                QuantaState.AWAITING_CONFIRMATION,
                QuantaState.SUCCESS,
                QuantaState.ERROR,
                QuantaState.CANCELLED,
            }
        ),
        QuantaState.AWAITING_INPUT: frozenset(
            {
                QuantaState.PROCESSING,
                QuantaState.CANCELLED,
                QuantaState.EXPIRED,
            }
        ),
        QuantaState.AWAITING_CONFIRMATION: frozenset(
            {
                QuantaState.EXECUTING,
                QuantaState.CANCELLED,
                QuantaState.EXPIRED,
            }
        ),
        QuantaState.EXECUTING: frozenset(
            {
                QuantaState.SUCCESS,
                QuantaState.ERROR,
            }
        ),
        QuantaState.SUCCESS: frozenset(),
        QuantaState.ERROR: frozenset(
            {
                QuantaState.IDLE,
                QuantaState.PROCESSING,
            }
        ),
        QuantaState.CANCELLED: frozenset(
            {
                QuantaState.IDLE,
            }
        ),
        QuantaState.EXPIRED: frozenset(
            {
                QuantaState.IDLE,
                QuantaState.PROCESSING,
            }
        ),
    }

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