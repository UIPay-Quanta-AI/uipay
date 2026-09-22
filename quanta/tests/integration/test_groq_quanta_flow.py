import pytest
from pydantic import BaseModel

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.config import Settings
from app.core.context import RequestContext
from app.orchestration.orchestrator import Orchestrator
from app.providers.llm.groq import GroqProvider
from app.schemas.response import ResponseStatus
from app.tools.base import Tool, ToolClassification, ToolResult
from app.tools.executor import ToolExecutor
from app.tools.implementations.beneficiary import SearchBeneficiaryTool
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
@pytest.mark.integration
async def test_groq_quanta_flow_with_mock_uipay():
    settings = Settings()

    if not settings.GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY is not configured.")

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
        description = "Prepare a transfer of money to a beneficiary."
        classification = ToolClassification.WRITE
        input_model = PrepareTransferInput
        output_model = PrepareTransferOutput

        async def execute(self, *, context, arguments):
            return ToolResult(
                success=True,
                data={"reference": "prep-groq-123"},
            )

    registry = ToolRegistry()
    registry.register(SearchBeneficiaryTool(client=ui_pay))
    registry.register(PrepareTransferTool())

    executor = ToolExecutor(
        registry=registry,
        policy=ToolPolicy(),
    )

    provider = GroqProvider(settings=settings)

    orchestrator = Orchestrator(
        llm_provider=provider,
        tool_registry=registry,
        tool_executor=executor,
        system_prompt=(
            "You are Quanta. When the user asks to send money to a contact, "
            "first use search_beneficiary to find them, then use prepare_transfer."
        ),
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
    assert response.data["reference"] == "prep-groq-123"
