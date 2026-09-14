import pytest

from app.core.context import RequestContext
from app.schemas.states import QuantaState
from app.tools.base import (
    ToolArgumentError,
    ToolExecutionError,
    ToolNotAllowedError,
    ToolResult,
)
from app.tools.executor import ToolExecutor
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry
from tests.unit.tools.test_base import (
    DummyTool,
)


def make_context() -> RequestContext:
    return RequestContext.create(
        user_id="user-123",
        session_id="session-123",
        operation="voice",
    )


def make_executor(tool=None) -> ToolExecutor:
    registry = ToolRegistry()

    if tool is not None:
        registry.register(tool)

    return ToolExecutor(
        registry=registry,
        policy=ToolPolicy(),
    )


@pytest.mark.asyncio
async def test_executor_runs_valid_tool():
    executor = make_executor(DummyTool())

    result = await executor.execute(
        tool_name="dummy_tool",
        arguments={"value": "hello"},
        context=make_context(),
        state=QuantaState.PROCESSING,
    )

    assert result.success is True
    assert result.data == {"result": "hello"}


@pytest.mark.asyncio
async def test_executor_rejects_invalid_arguments():
    executor = make_executor(DummyTool())

    with pytest.raises(
        ToolArgumentError,
        match="Invalid arguments",
    ):
        await executor.execute(
            tool_name="dummy_tool",
            arguments={"value": 123},
            context=make_context(),
            state=QuantaState.PROCESSING,
        )


@pytest.mark.asyncio
async def test_executor_rejects_missing_arguments():
    executor = make_executor(DummyTool())

    with pytest.raises(ToolArgumentError):
        await executor.execute(
            tool_name="dummy_tool",
            arguments={},
            context=make_context(),
            state=QuantaState.PROCESSING,
        )


@pytest.mark.asyncio
async def test_executor_rejects_terminal_state():
    executor = make_executor(DummyTool())

    with pytest.raises(
        ToolNotAllowedError,
        match="terminal state",
    ):
        await executor.execute(
            tool_name="dummy_tool",
            arguments={"value": "hello"},
            context=make_context(),
            state=QuantaState.SUCCESS,
        )


@pytest.mark.asyncio
async def test_executor_does_not_allow_user_id_from_arguments():
    executor = make_executor(DummyTool())

    result = await executor.execute(
        tool_name="dummy_tool",
        arguments={
            "value": "hello",
            "user_id": "attacker-user",
        },
        context=make_context(),
        state=QuantaState.PROCESSING,
    )

    assert result.success is True
    assert result.data == {"result": "hello"}


class InvalidResultTool(DummyTool):
    name = "invalid_result_tool"

    async def execute(
        self,
        *,
        context,
        arguments,
    ):
        return {"not": "a ToolResult"}


@pytest.mark.asyncio
async def test_executor_rejects_invalid_tool_result():
    executor = make_executor(InvalidResultTool())

    with pytest.raises(
        ToolExecutionError,
        match="invalid result",
    ):
        await executor.execute(
            tool_name="invalid_result_tool",
            arguments={"value": "hello"},
            context=make_context(),
            state=QuantaState.PROCESSING,
        )


class FailingTool(DummyTool):
    name = "failing_tool"

    async def execute(
        self,
        *,
        context,
        arguments,
    ):
        raise RuntimeError("backend exploded")


@pytest.mark.asyncio
async def test_executor_normalizes_unexpected_tool_failure():
    executor = make_executor(FailingTool())

    with pytest.raises(
        ToolExecutionError,
        match="Tool execution failed",
    ):
        await executor.execute(
            tool_name="failing_tool",
            arguments={"value": "hello"},
            context=make_context(),
            state=QuantaState.PROCESSING,
        )


class InvalidDataTool(DummyTool):
    name = "invalid_data_tool"

    async def execute(
        self,
        *,
        context,
        arguments,
    ):
        return ToolResult(
            success=True,
            data={"wrong_field": 123},
        )


@pytest.mark.asyncio
async def test_executor_rejects_invalid_tool_output():
    executor = make_executor(InvalidDataTool())

    with pytest.raises(
        ToolExecutionError,
        match="invalid data",
    ):
        await executor.execute(
            tool_name="invalid_data_tool",
            arguments={"value": "hello"},
            context=make_context(),
            state=QuantaState.PROCESSING,
        )


class EmptySuccessfulTool(DummyTool):
    name = "empty_successful_tool"

    async def execute(
        self,
        *,
        context,
        arguments,
    ):
        return ToolResult(
            success=True,
            data=None,
        )


@pytest.mark.asyncio
async def test_executor_rejects_success_without_data():
    executor = make_executor(EmptySuccessfulTool())

    with pytest.raises(
        ToolExecutionError,
        match="no data",
    ):
        await executor.execute(
            tool_name="empty_successful_tool",
            arguments={"value": "hello"},
            context=make_context(),
            state=QuantaState.PROCESSING,
        )
