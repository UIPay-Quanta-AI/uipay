from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.core.context import RequestContext
from app.orchestration.orchestrator import (
    Orchestrator,
)
from app.providers.base import ProviderError
from app.providers.llm.base import (
    LLMResponse,
    LLMToolCall,
)
from app.schemas.response import ResponseStatus
from app.schemas.states import QuantaState
from app.tools.base import ToolResult
from app.tools.executor import ToolExecutor
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry
from tests.unit.tools.test_base import DummyTool


def make_context() -> RequestContext:
    return RequestContext.create(
        user_id="user-123",
        session_id="session-123",
        operation="voice",
    )


class MockLLMProvider:
    def __init__(
        self,
        responses: list[LLMResponse],
    ) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def generate(
        self,
        *,
        messages,
        system_prompt=None,
        tools=None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "messages": messages,
                "system_prompt": system_prompt,
                "tools": tools,
            }
        )

        if not self.responses:
            raise AssertionError("MockLLMProvider has no response configured.")

        return self.responses.pop(0)


class FailingLLMProvider:
    async def generate(
        self,
        *,
        messages,
        system_prompt=None,
        tools=None,
    ) -> LLMResponse:
        raise ProviderError("LLM unavailable")


def make_executor(
    tool=None,
) -> ToolExecutor:
    registry = ToolRegistry()

    if tool is not None:
        registry.register(tool)

    return ToolExecutor(
        registry=registry,
        policy=ToolPolicy(),
    )


def make_orchestrator(
    *,
    llm_provider,
    tool=None,
    max_tool_iterations=5,
) -> Orchestrator:
    registry = ToolRegistry()

    if tool is not None:
        registry.register(tool)

    executor = ToolExecutor(
        registry=registry,
        policy=ToolPolicy(),
    )

    return Orchestrator(
        llm_provider=llm_provider,
        tool_registry=registry,
        tool_executor=executor,
        max_tool_iterations=max_tool_iterations,
    )


@pytest.mark.asyncio
async def test_orchestrator_returns_final_llm_response():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content="Your balance is available.",
                finish_reason="end_turn",
            )
        ]
    )

    orchestrator = make_orchestrator(
        llm_provider=llm,
    )

    response = await orchestrator.process(
        context=make_context(),
        user_input="What is my balance?",
    )

    assert response.status == ResponseStatus.SUCCESS
    assert response.request_id
    assert response.speech is not None
    assert response.speech.text == "Your balance is available."


@pytest.mark.asyncio
async def test_orchestrator_passes_registered_tools_to_llm():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content="Done.",
            )
        ]
    )

    orchestrator = make_orchestrator(
        llm_provider=llm,
        tool=DummyTool(),
    )

    await orchestrator.process(
        context=make_context(),
        user_input="Do something.",
    )

    assert len(llm.calls) == 1

    tools = llm.calls[0]["tools"]

    assert len(tools) == 1
    assert tools[0]["name"] == "dummy_tool"


@pytest.mark.asyncio
async def test_orchestrator_executes_llm_requested_tool():
    llm = MockLLMProvider(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-1",
                        name="dummy_tool",
                        arguments={
                            "value": "hello",
                        },
                    )
                ]
            ),
            LLMResponse(
                content="The operation is complete.",
            ),
        ]
    )

    orchestrator = make_orchestrator(
        llm_provider=llm,
        tool=DummyTool(),
    )

    response = await orchestrator.process(
        context=make_context(),
        user_input="Run the tool.",
    )

    assert response.status == ResponseStatus.SUCCESS
    assert response.speech is not None
    assert response.speech.text == "The operation is complete."

    assert len(llm.calls) == 2

    second_messages = llm.calls[1]["messages"]

    tool_messages = [message for message in second_messages if message.role.value == "tool"]

    assert len(tool_messages) == 1
    assert tool_messages[0].tool_call_id == "call-1"
    assert '"success":true' in tool_messages[0].content


@pytest.mark.asyncio
async def test_orchestrator_preserves_user_context_for_tool_execution():
    class ContextAwareOutput(BaseModel):
        user_id: str
        value: str

    class ContextAwareTool(DummyTool):
        name = "context_aware_tool"
        output_model = ContextAwareOutput

        async def execute(
            self,
            *,
            context,
            arguments,
        ):
            return ToolResult(
                success=True,
                data={
                    "user_id": context.user_id,
                    "value": arguments.value,
                },
            )

    tool = ContextAwareTool()

    llm = MockLLMProvider(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-1",
                        name="context_aware_tool",
                        arguments={
                            "value": "hello",
                        },
                    )
                ]
            ),
            LLMResponse(
                content="Done.",
            ),
        ]
    )

    orchestrator = make_orchestrator(
        llm_provider=llm,
        tool=tool,
    )

    response = await orchestrator.process(
        context=make_context(),
        user_input="Do it.",
    )

    assert response.status == ResponseStatus.SUCCESS

    second_messages = llm.calls[1]["messages"]

    tool_message = next(message for message in second_messages if message.role.value == "tool")

    assert '"user_id":"user-123"' in tool_message.content


@pytest.mark.asyncio
async def test_orchestrator_handles_provider_failure():
    orchestrator = make_orchestrator(
        llm_provider=FailingLLMProvider(),
    )

    response = await orchestrator.process(
        context=make_context(),
        user_input="Hello.",
    )

    assert response.status == ResponseStatus.ERROR
    assert response.error is not None
    assert response.error.code == "PROVIDER_ERROR"

    assert response.speech is not None
    assert response.speech.text == "I'm having trouble processing that right now."


@pytest.mark.asyncio
async def test_orchestrator_enforces_max_tool_iterations():
    llm = MockLLMProvider(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-1",
                        name="dummy_tool",
                        arguments={
                            "value": "one",
                        },
                    )
                ]
            ),
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-2",
                        name="dummy_tool",
                        arguments={
                            "value": "two",
                        },
                    )
                ]
            ),
        ]
    )

    orchestrator = make_orchestrator(
        llm_provider=llm,
        tool=DummyTool(),
        max_tool_iterations=2,
    )

    response = await orchestrator.process(
        context=make_context(),
        user_input="Keep going.",
    )

    assert response.status == ResponseStatus.ERROR
    assert response.error is not None
    assert response.error.code == "MAX_TOOL_ITERATIONS"

    assert len(llm.calls) == 2


@pytest.mark.asyncio
async def test_orchestrator_rejects_invalid_initial_state():
    llm = MockLLMProvider(
        [
            LLMResponse(
                content="Should not run.",
            )
        ]
    )

    orchestrator = make_orchestrator(
        llm_provider=llm,
    )

    response = await orchestrator.process(
        context=make_context(),
        user_input="Hello.",
        initial_state=QuantaState.SUCCESS,
    )

    assert response.status == ResponseStatus.ERROR
    assert response.error is not None
    assert response.error.code == "INVALID_INITIAL_STATE"

    assert len(llm.calls) == 0


@pytest.mark.asyncio
async def test_orchestrator_rejects_unknown_tool():
    llm = MockLLMProvider(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-unknown",
                        name="does_not_exist",
                        arguments={},
                    )
                ]
            )
        ]
    )

    orchestrator = make_orchestrator(
        llm_provider=llm,
    )

    response = await orchestrator.process(
        context=make_context(),
        user_input="Use the unknown tool.",
    )

    assert response.status == ResponseStatus.ERROR
    assert response.error is not None
    assert response.error.code == "TOOL_ERROR"


@pytest.mark.asyncio
async def test_orchestrator_does_not_accept_user_id_from_llm_arguments():
    llm = MockLLMProvider(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-1",
                        name="dummy_tool",
                        arguments={
                            "value": "hello",
                            "user_id": "attacker-user",
                        },
                    )
                ]
            ),
            LLMResponse(
                content="Done.",
            ),
        ]
    )

    orchestrator = make_orchestrator(
        llm_provider=llm,
        tool=DummyTool(),
    )

    response = await orchestrator.process(
        context=make_context(),
        user_input="Do it.",
    )

    assert response.status == ResponseStatus.SUCCESS

    second_messages = llm.calls[1]["messages"]

    tool_message = next(message for message in second_messages if message.role.value == "tool")

    assert "attacker-user" not in tool_message.content


@pytest.mark.asyncio
async def test_prepare_transfer_stops_orchestration_for_confirmation():
    class PrepareTransferOutput(BaseModel):
        reference: str

    class PrepareTransferTool(DummyTool):
        name = "prepare_transfer"
        output_model = PrepareTransferOutput

        async def execute(
            self,
            *,
            context,
            arguments,
        ):
            return ToolResult(
                success=True,
                data={
                    "reference": "prep-123",
                },
            )

    llm = MockLLMProvider(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-transfer",
                        name="prepare_transfer",
                        arguments={
                            "value": "5000",
                        },
                    )
                ]
            ),
        ]
    )

    orchestrator = make_orchestrator(
        llm_provider=llm,
        tool=PrepareTransferTool(),
    )

    response = await orchestrator.process(
        context=make_context(),
        user_input="Send five thousand naira.",
    )

    assert response.status == ResponseStatus.CONFIRMATION_REQUIRED
    assert response.ui.type == "transfer_confirmation"

    assert response.data is not None
    assert response.data["reference"] == "prep-123"

    # Most importantly: Claude was called exactly once.
    assert len(llm.calls) == 1


def test_failed_prepare_transfer_does_not_transition_to_confirmation():
    from app.orchestration.state_machine import StateMachine

    state_machine = StateMachine(
        current_state=QuantaState.PROCESSING,
    )

    Orchestrator._apply_deterministic_state_rules(
        tool_name="prepare_transfer",
        result=ToolResult(
            success=False,
            error_code="VALIDATION_FAILED",
            error_message="Invalid transfer.",
        ),
        state_machine=state_machine,
    )

    assert state_machine.current_state == QuantaState.PROCESSING


@pytest.mark.asyncio
async def test_prepare_transfer_failure_does_not_request_confirmation():
    class PrepareTransferOutput(BaseModel):
        reference: str

    class PrepareTransferTool(DummyTool):
        name = "prepare_transfer"
        output_model = PrepareTransferOutput

        async def execute(
            self,
            *,
            context,
            arguments,
        ):
            return ToolResult(
                success=False,
                error_code="TRANSFER_INVALID",
                error_message="Transfer could not be prepared.",
            )

    llm = MockLLMProvider(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call-transfer",
                        name="prepare_transfer",
                        arguments={
                            "value": "5000",
                        },
                    )
                ]
            ),
            LLMResponse(
                content="I could not prepare that transfer.",
            ),
        ]
    )

    orchestrator = make_orchestrator(
        llm_provider=llm,
        tool=PrepareTransferTool(),
    )

    response = await orchestrator.process(
        context=make_context(),
        user_input="Send five thousand naira.",
    )

    assert response.status == ResponseStatus.SUCCESS
    assert len(llm.calls) == 2
