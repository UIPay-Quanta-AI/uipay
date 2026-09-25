from __future__ import annotations

from app.domain.state.models import QuantaState


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
            f"Invalid state transition: {current_state.value} -> {requested_state.value}"
        )


ALLOWED_STATE_TRANSITIONS: dict[QuantaState, frozenset[QuantaState]] = {
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
