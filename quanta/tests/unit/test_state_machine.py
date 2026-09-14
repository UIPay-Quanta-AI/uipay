import pytest

from app.orchestration.state_machine import (
    InvalidStateTransitionError,
    StateMachine,
)
from app.schemas.states import QuantaState


def test_initial_state_is_idle():
    state_machine = StateMachine()

    assert state_machine.current_state == QuantaState.IDLE


def test_idle_can_transition_to_processing():
    state_machine = StateMachine()

    state_machine.transition(QuantaState.PROCESSING)

    assert state_machine.current_state == QuantaState.PROCESSING


def test_processing_can_transition_to_awaiting_input():
    state_machine = StateMachine(
        current_state=QuantaState.PROCESSING
    )

    state_machine.transition(QuantaState.AWAITING_INPUT)

    assert state_machine.current_state == QuantaState.AWAITING_INPUT


def test_processing_can_transition_to_awaiting_confirmation():
    state_machine = StateMachine(
        current_state=QuantaState.PROCESSING
    )

    state_machine.transition(QuantaState.AWAITING_CONFIRMATION)

    assert state_machine.current_state == QuantaState.AWAITING_CONFIRMATION


def test_processing_can_transition_to_success():
    state_machine = StateMachine(
        current_state=QuantaState.PROCESSING
    )

    state_machine.transition(QuantaState.SUCCESS)

    assert state_machine.current_state == QuantaState.SUCCESS


def test_processing_can_transition_to_error():
    state_machine = StateMachine(
        current_state=QuantaState.PROCESSING
    )

    state_machine.transition(QuantaState.ERROR)

    assert state_machine.current_state == QuantaState.ERROR


def test_processing_can_transition_to_cancelled():
    state_machine = StateMachine(
        current_state=QuantaState.PROCESSING
    )

    state_machine.transition(QuantaState.CANCELLED)

    assert state_machine.current_state == QuantaState.CANCELLED


def test_awaiting_input_can_return_to_processing():
    state_machine = StateMachine(
        current_state=QuantaState.AWAITING_INPUT
    )

    state_machine.transition(QuantaState.PROCESSING)

    assert state_machine.current_state == QuantaState.PROCESSING


def test_awaiting_input_can_be_cancelled():
    state_machine = StateMachine(
        current_state=QuantaState.AWAITING_INPUT
    )

    state_machine.transition(QuantaState.CANCELLED)

    assert state_machine.current_state == QuantaState.CANCELLED


def test_awaiting_input_can_expire():
    state_machine = StateMachine(
        current_state=QuantaState.AWAITING_INPUT
    )

    state_machine.transition(QuantaState.EXPIRED)

    assert state_machine.current_state == QuantaState.EXPIRED


def test_confirmation_can_transition_to_executing():
    state_machine = StateMachine(
        current_state=QuantaState.AWAITING_CONFIRMATION
    )

    state_machine.transition(QuantaState.EXECUTING)

    assert state_machine.current_state == QuantaState.EXECUTING


def test_confirmation_can_be_cancelled():
    state_machine = StateMachine(
        current_state=QuantaState.AWAITING_CONFIRMATION
    )

    state_machine.transition(QuantaState.CANCELLED)

    assert state_machine.current_state == QuantaState.CANCELLED


def test_confirmation_can_expire():
    state_machine = StateMachine(
        current_state=QuantaState.AWAITING_CONFIRMATION
    )

    state_machine.transition(QuantaState.EXPIRED)

    assert state_machine.current_state == QuantaState.EXPIRED


def test_executing_can_transition_to_success():
    state_machine = StateMachine(
        current_state=QuantaState.EXECUTING
    )

    state_machine.transition(QuantaState.SUCCESS)

    assert state_machine.current_state == QuantaState.SUCCESS


def test_executing_can_transition_to_error():
    state_machine = StateMachine(
        current_state=QuantaState.EXECUTING
    )

    state_machine.transition(QuantaState.ERROR)

    assert state_machine.current_state == QuantaState.ERROR


def test_error_can_return_to_idle():
    state_machine = StateMachine(
        current_state=QuantaState.ERROR
    )

    state_machine.transition(QuantaState.IDLE)

    assert state_machine.current_state == QuantaState.IDLE


def test_error_can_restart_processing():
    state_machine = StateMachine(
        current_state=QuantaState.ERROR
    )

    state_machine.transition(QuantaState.PROCESSING)

    assert state_machine.current_state == QuantaState.PROCESSING


def test_cancelled_can_return_to_idle():
    state_machine = StateMachine(
        current_state=QuantaState.CANCELLED
    )

    state_machine.transition(QuantaState.IDLE)

    assert state_machine.current_state == QuantaState.IDLE


def test_expired_can_return_to_idle():
    state_machine = StateMachine(
        current_state=QuantaState.EXPIRED
    )

    state_machine.transition(QuantaState.IDLE)

    assert state_machine.current_state == QuantaState.IDLE


def test_expired_can_restart_processing():
    state_machine = StateMachine(
        current_state=QuantaState.EXPIRED
    )

    state_machine.transition(QuantaState.PROCESSING)

    assert state_machine.current_state == QuantaState.PROCESSING


def test_invalid_transition_raises_error():
    state_machine = StateMachine()

    with pytest.raises(
        InvalidStateTransitionError,
        match="Invalid state transition: idle -> success",
    ):
        state_machine.transition(QuantaState.SUCCESS)


def test_cannot_skip_confirmation_for_financial_flow():
    state_machine = StateMachine(
        current_state=QuantaState.PROCESSING
    )

    with pytest.raises(InvalidStateTransitionError):
        state_machine.transition(QuantaState.EXECUTING)


def test_cannot_execute_from_awaiting_input():
    state_machine = StateMachine(
        current_state=QuantaState.AWAITING_INPUT
    )

    with pytest.raises(InvalidStateTransitionError):
        state_machine.transition(QuantaState.EXECUTING)


def test_success_is_terminal():
    state_machine = StateMachine(
        current_state=QuantaState.SUCCESS
    )

    assert not state_machine.can_transition(QuantaState.IDLE)
    assert not state_machine.can_transition(QuantaState.PROCESSING)


def test_reset_from_error():
    state_machine = StateMachine(
        current_state=QuantaState.ERROR
    )

    state_machine.reset()

    assert state_machine.current_state == QuantaState.IDLE


def test_reset_from_cancelled():
    state_machine = StateMachine(
        current_state=QuantaState.CANCELLED
    )

    state_machine.reset()

    assert state_machine.current_state == QuantaState.IDLE


def test_reset_from_expired():
    state_machine = StateMachine(
        current_state=QuantaState.EXPIRED
    )

    state_machine.reset()

    assert state_machine.current_state == QuantaState.IDLE


def test_reset_does_not_bypass_success_terminal_state():
    state_machine = StateMachine(
        current_state=QuantaState.SUCCESS
    )

    with pytest.raises(InvalidStateTransitionError):
        state_machine.reset()

    assert state_machine.current_state == QuantaState.SUCCESS

def test_all_states_have_transition_definitions():
    for state in QuantaState:
        assert state in StateMachine._ALLOWED_TRANSITIONS

def test_invalid_transition_does_not_mutate_state():
    state_machine = StateMachine(
        current_state=QuantaState.PROCESSING
    )

    with pytest.raises(InvalidStateTransitionError):
        state_machine.transition(QuantaState.EXECUTING)

    assert state_machine.current_state == QuantaState.PROCESSING

def test_complete_transfer_lifecycle():
    state_machine = StateMachine()

    state_machine.transition(QuantaState.PROCESSING)
    assert state_machine.current_state == QuantaState.PROCESSING

    state_machine.transition(QuantaState.AWAITING_CONFIRMATION)
    assert (
        state_machine.current_state
        == QuantaState.AWAITING_CONFIRMATION
    )

    state_machine.transition(QuantaState.EXECUTING)
    assert state_machine.current_state == QuantaState.EXECUTING

    state_machine.transition(QuantaState.SUCCESS)
    assert state_machine.current_state == QuantaState.SUCCESS

def test_confirmation_expiration_lifecycle():
    state_machine = StateMachine()

    state_machine.transition(QuantaState.PROCESSING)
    state_machine.transition(QuantaState.AWAITING_CONFIRMATION)
    state_machine.transition(QuantaState.EXPIRED)

    assert state_machine.current_state == QuantaState.EXPIRED

    state_machine.transition(QuantaState.IDLE)

    assert state_machine.current_state == QuantaState.IDLE