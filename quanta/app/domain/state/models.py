from __future__ import annotations

from enum import Enum


class QuantaState(str, Enum):
    """
    States representing the lifecycle of a Quanta operation.

    State transitions are controlled by the application state machine.
    External actors such as Claude, ASR, OCR, and the client must not
    directly mutate the current state.
    """

    IDLE = "idle"
    PROCESSING = "processing"
    AWAITING_INPUT = "awaiting_input"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING = "executing"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


# Alias for domain naming convention in implementation plan
ApplicationState = QuantaState
