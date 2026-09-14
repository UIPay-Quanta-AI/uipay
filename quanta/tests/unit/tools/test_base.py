import inspect

import pytest
from pydantic import BaseModel

from app.tools.base import (
    Tool,
    ToolClassification,
    ToolResult,
)


class DummyInput(BaseModel):
    value: str


class DummyOutput(BaseModel):
    result: str


class DummyTool(Tool[DummyInput, DummyOutput]):
    name = "dummy_tool"
    description = "A test tool"
    classification = ToolClassification.READ
    input_model = DummyInput
    output_model = DummyOutput

    async def execute(
        self,
        *,
        context,
        arguments,
    ):
        return ToolResult(
            success=True,
            data={"result": arguments.value},
        )


def test_tool_base_is_abstract():
    assert inspect.isabstract(Tool)


@pytest.mark.asyncio
async def test_tool_definition():
    tool = DummyTool()

    definition = tool.definition()

    assert definition["name"] == "dummy_tool"
    assert definition["description"] == "A test tool"
    assert "input_schema" in definition


@pytest.mark.asyncio
async def test_tool_execution_contract():
    from app.core.context import RequestContext

    tool = DummyTool()

    context = RequestContext.create(
        user_id="user-123",
        session_id="session-123",
        operation="voice",
    )

    result = await tool.execute(
        context=context,
        arguments=DummyInput(value="hello"),
    )

    assert result.success is True
    assert result.data == {"result": "hello"}
