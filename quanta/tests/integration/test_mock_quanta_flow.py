import pytest
from pydantic import BaseModel

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.orchestration.orchestrator import Orchestrator
from app.providers.llm.base import (
    LLMResponse,
    LLMToolCall,
)
from app.providers.llm.mock import MockLLMProvider
from app.schemas.response import ResponseStatus
from app.tools.base import Tool, ToolClassification, ToolResult
from app.tools.executor import ToolExecutor
from app.tools.implementations.beneficiary import SearchBeneficiaryTool
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_mock_provider_transfer_flow_reaches_confirmation():
    ui_pay = MockUIPayClient(
        beneficiaries=[
            {
                "id": "ben_001",
                "user_id": "user_001",
                "nickname": "Mum",
                "account_name": "Amaka Okafor",
                "bank_name": "GTBank",
                "account_number": "0123456789",
            }
        ]
    )

    class PrepareTransferInput(BaseModel):
        beneficiary_id: str
        amount: int

    class PrepareTransferOutput(BaseModel):
        reference: str

    class PrepareTransferTool(Tool[PrepareTransferInput, PrepareTransferOutput]):
        name = "prepare_transfer"
        description = "Prepare a transfer"
        classification = ToolClassification.WRITE
        input_model = PrepareTransferInput
        output_model = PrepareTransferOutput

        async def execute(self, *, context, arguments):
            return ToolResult(
                success=True,
                data={"reference": "prep-123"},
            )

    registry = ToolRegistry()
    registry.register(SearchBeneficiaryTool(client=ui_pay))
    registry.register(PrepareTransferTool())

    executor = ToolExecutor(
        registry=registry,
        policy=ToolPolicy(),
    )

    responses = [
        LLMResponse(
            tool_calls=[
                LLMToolCall(
                    id="call_search",
                    name="search_beneficiary",
                    arguments={"query": "Mum"},
                )
            ]
        ),
        LLMResponse(
            tool_calls=[
                LLMToolCall(
                    id="call_prepare",
                    name="prepare_transfer",
                    arguments={
                        "beneficiary_id": "ben_001",
                        "amount": 5000,
                    },
                )
            ]
        ),
    ]

    llm = MockLLMProvider(responses=responses)

    orchestrator = Orchestrator(
        llm_provider=llm,
        tool_registry=registry,
        tool_executor=executor,
    )

    context = RequestContext.create(
        user_id="user_001",
        session_id="session_001",
        operation="transfer",
    )

    response = await orchestrator.process(
        context=context,
        user_input="Send ₦5,000 to Mum.",
    )

    assert response.status == ResponseStatus.CONFIRMATION_REQUIRED
    assert response.ui.type == "transfer_confirmation"
    assert response.data is not None
    assert response.data["reference"] == "prep-123"
    assert len(llm.calls) == 2
