import pytest

from app.core.context import RequestContext
from app.schemas.states import QuantaState
from app.tools.base import (
    ToolClassification,
    ToolNotAllowedError,
)
from app.tools.policy import ToolPolicy
from tests.unit.tools.test_base import DummyTool


def make_context() -> RequestContext:
    return RequestContext.create(
        user_id="user-123",
        session_id="session-123",
        operation="voice",
    )


def test_policy_allows_authenticated_read_tool():
    policy = ToolPolicy()

    policy.check(
        tool=DummyTool(),
        context=make_context(),
        state=QuantaState.PROCESSING,
    )


def test_policy_rejects_empty_user_identity():
    policy = ToolPolicy()

    context = RequestContext.create(
        user_id="valid-user",
        session_id="session-123",
        operation="voice",
    )

    # RequestContext itself prevents empty user IDs, so this test verifies
    # the policy contract using a controlled object-level mutation attempt.
    object.__setattr__(context, "user_id", "")

    with pytest.raises(
        ToolNotAllowedError,
        match="Authenticated user context is required",
    ):
        policy.check(
            tool=DummyTool(),
            context=context,
            state=QuantaState.PROCESSING,
        )


@pytest.mark.parametrize(
    "state",
    [
        QuantaState.SUCCESS,
        QuantaState.CANCELLED,
        QuantaState.EXPIRED,
    ],
)
def test_policy_rejects_terminal_states(state):
    policy = ToolPolicy()

    with pytest.raises(
        ToolNotAllowedError,
        match="terminal state",
    ):
        policy.check(
            tool=DummyTool(),
            context=make_context(),
            state=state,
        )


def test_policy_rejects_system_tools():
    class SystemTool(DummyTool):
        name = "system_tool"
        classification = ToolClassification.SYSTEM

    policy = ToolPolicy()

    with pytest.raises(
        ToolNotAllowedError,
        match="System tool",
    ):
        policy.check(
            tool=SystemTool(),
            context=make_context(),
            state=QuantaState.PROCESSING,
        )
