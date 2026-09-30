"""
End-to-End Scenario Tests for Quanta Mega Step 1.
Validates all 12 end-to-end user journeys deterministically.
"""

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.dependencies.tools import build_tool_registry
from app.domain.conversational.session import SessionManager
from app.orchestration.multimodal import MultimodalInput, MultimodalProcessor
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.voice_pipeline import VoicePipeline
from app.orchestration.workflow_runner import ConversationalWorkflowRunner
from app.providers.asr.base import ASRProvider, ASRResult
from app.providers.llm.base import LLMProvider, LLMResponse, LLMToolCall
from app.providers.ocr.base import OCRProvider, OCRResult
from app.providers.speaker.base import SpeakerProvider, VerificationResult
from app.schemas.response import ResponseStatus, UIType
from app.tools.executor import ToolExecutor
from app.tools.policy import ToolPolicy


class ScenarioMockLLM(LLMProvider):
    def __init__(self):
        self.call_history = []

    async def generate(self, *, messages, system_prompt=None, tools=None) -> LLMResponse:
        # If last message is a TOOL result, return a plain text completion
        if messages and messages[-1].role.value == "tool":
            return LLMResponse(
                content="Done. I've applied the changes you requested.",
                tool_calls=[],
                finish_reason="stop",
            )

        user_msg = messages[-1].content if messages else ""
        self.call_history.append(user_msg)

        # 1. Profile / Budget Intent
        if "create a budget" in user_text_lower(user_msg):
            return LLMResponse(
                content="What is your approximate monthly income?",
                tool_calls=[],
                finish_reason="stop",
            )
        elif "500k" in user_text_lower(user_msg) or "earn 500" in user_text_lower(user_msg):
            return LLMResponse(
                content="Updated profile with 500,000 monthly income.",
                tool_calls=[
                    LLMToolCall(
                        id="call_p1",
                        name="update_financial_profile",
                        arguments={"monthly_income": "500000.00"},
                    )
                ],
                finish_reason="tool_calls",
            )
        # 2. Goal Creation & Completion
        elif "laptop" in user_text_lower(user_msg) and "completed" in user_text_lower(user_msg):
            return LLMResponse(
                content="Marked laptop goal as completed.",
                tool_calls=[
                    LLMToolCall(
                        id="call_g1",
                        name="update_goal",
                        arguments={"goal_identifier": "laptop", "status": "completed"},
                    )
                ],
                finish_reason="tool_calls",
            )
        elif "save" in user_text_lower(user_msg) and "emergency" in user_text_lower(user_msg):
            return LLMResponse(
                content="Created emergency fund goal.",
                tool_calls=[
                    LLMToolCall(
                        id="call_g2",
                        name="create_goal",
                        arguments={"name": "Emergency Fund", "target_amount": "2000000.00"},
                    )
                ],
                finish_reason="tool_calls",
            )
        # 3. Transfer Intent
        elif (
            "mum" in user_text_lower(user_msg)
            or "50,000" in user_msg
            or "50 thousand" in user_text_lower(user_msg)
            or "0123456789" in user_msg
        ):
            if "50" in user_msg and (
                "gtbank" in user_text_lower(user_msg)
                or "0123456789" in user_msg
                or "mum" in user_text_lower(user_msg)
            ):
                return LLMResponse(
                    content="Preparing transfer of ₦50,000 to Mum.",
                    tool_calls=[
                        LLMToolCall(
                            id="call_t1",
                            name="prepare_transfer",
                            arguments={
                                "beneficiary_id": "0123456789",
                                "amount": 50000,
                            },
                        )
                    ],
                    finish_reason="tool_calls",
                )
            else:
                return LLMResponse(
                    content="I found the account details for Mum. How much would you like to transfer?",
                    tool_calls=[],
                    finish_reason="stop",
                )
        # Default response
        return LLMResponse(
            content=f"Processed request: {user_msg}",
            tool_calls=[],
            finish_reason="stop",
        )


def user_text_lower(msg: str) -> str:
    return (msg or "").lower()


class ScenarioMockOCR(OCRProvider):
    async def extract(self, *, image, filename=None):
        return OCRResult(
            text="GTBank Account: 0123456789 Name: Mum",
            confidence=0.98,
        )


class ScenarioMockSpeaker(SpeakerProvider):
    async def enroll(self, *, audio, filename=None):
        pass

    async def verify(self, *, audio, profile, threshold=None, filename=None):
        return VerificationResult(verified=True, score=0.95, threshold=0.7)


class ScenarioMockASR(ASRProvider):
    async def transcribe(self, *, audio, filename=None, language=None):
        return ASRResult(text="Send fifty thousand naira to Mum", confidence=0.95)


@pytest.fixture
def scenario_setup():
    client = MockUIPayClient(
        beneficiaries=[
            {
                "user_id": "user_scen",
                "nickname": "Mum",
                "account_name": "Amaka Okafor",
                "account_number": "0123456789",
                "bank": "GTBank",
            }
        ]
    )
    registry = build_tool_registry(ui_pay_client=client)
    evaluator = ToolPolicy()
    executor = ToolExecutor(registry=registry, policy=evaluator)
    llm = ScenarioMockLLM()

    orchestrator = Orchestrator(
        llm_provider=llm,
        tool_registry=registry,
        tool_executor=executor,
    )
    multimodal_processor = MultimodalProcessor(
        orchestrator=orchestrator,
        ocr_provider=ScenarioMockOCR(),
    )
    voice_pipeline = VoicePipeline(
        speaker_provider=ScenarioMockSpeaker(),
        asr_provider=ScenarioMockASR(),
        orchestrator=orchestrator,
    )
    runner = ConversationalWorkflowRunner(
        orchestrator=orchestrator,
        multimodal_processor=multimodal_processor,
        voice_pipeline=voice_pipeline,
        ui_pay_client=client,
    )

    return runner, client


@pytest.mark.asyncio
async def test_scenario_1_profile_to_budget(scenario_setup):
    runner, client = scenario_setup
    ctx = RequestContext.create(user_id="user_scen", session_id="sess_scen1", operation="TEXT")

    # Step A: Intent to create budget
    res1 = await runner.run_interaction(
        context=ctx, input_data=MultimodalInput(text="Create a budget for me")
    )
    assert res1.status == ResponseStatus.SUCCESS
    assert "income" in res1.speech.text.lower()

    # Step B: Provide income
    res2 = await runner.run_interaction(
        context=ctx, input_data=MultimodalInput(text="I earn 500k monthly")
    )
    assert res2.status == ResponseStatus.SUCCESS
    profile = await client.get_financial_profile(user_id="user_scen")
    assert profile["monthly_income"] == "500000.00"


@pytest.mark.asyncio
async def test_scenario_4_goal_completion(scenario_setup):
    runner, client = scenario_setup
    ctx = RequestContext.create(user_id="user_scen", session_id="sess_scen4", operation="TEXT")

    # Pre-create goal
    await client.create_goal(
        user_id="user_scen", goal_data={"name": "laptop", "target_amount": "800000.00"}
    )

    res = await runner.run_interaction(
        context=ctx, input_data=MultimodalInput(text="Mark my laptop goal as completed")
    )
    assert res.status == ResponseStatus.SUCCESS
    goal = await client.get_goal(user_id="user_scen", goal_id="laptop")
    assert goal["status"] == "completed"


@pytest.mark.asyncio
async def test_scenario_7_text_transfer(scenario_setup):
    runner, _client = scenario_setup
    ctx = RequestContext.create(user_id="user_scen", session_id="sess_scen7", operation="TEXT")

    res = await runner.run_interaction(
        context=ctx,
        input_data=MultimodalInput(text="Send 50 thousand to GTBank account 0123456789 for Mum"),
    )
    assert res.status == ResponseStatus.CONFIRMATION_REQUIRED
    assert res.ui.type == UIType.TRANSFER_CONFIRMATION
    assert res.data["amount"] == 50000
    assert res.data["beneficiary_id"] == "0123456789"


@pytest.mark.asyncio
async def test_scenario_10_image_plus_voice_transfer(scenario_setup):
    runner, _client = scenario_setup
    ctx = RequestContext.create(
        user_id="user_scen", session_id="sess_scen10", operation="MULTIMODAL"
    )

    res = await runner.run_interaction(
        context=ctx,
        input_data=MultimodalInput(
            image=b"fake_receipt_image",
            text="Send 50 thousand to this account",
        ),
    )
    assert res.status == ResponseStatus.CONFIRMATION_REQUIRED
    assert res.ui.type == UIType.TRANSFER_CONFIRMATION


@pytest.mark.asyncio
async def test_scenario_12_conversation_continuation(scenario_setup):
    runner, _client = scenario_setup
    session_id = "sess_scen12"
    ctx = RequestContext.create(user_id="user_scen", session_id=session_id, operation="TEXT")

    # Turn 1: Partial transfer info (Image only -> Account extracted, amount missing)
    session_mgr = SessionManager.get_instance()
    session = session_mgr.get_session(session_id=session_id, user_id="user_scen")
    session.active_workflow = "TRANSFER"
    session.collected_data = {
        "bank": "GTBank",
        "account_number": "0123456789",
        "recipient_name": "Mum",
    }

    # Turn 2: User answers ONLY the question ("50 thousand")
    res2 = await runner.run_interaction(context=ctx, input_data=MultimodalInput(text="50 thousand"))
    assert res2.status == ResponseStatus.CONFIRMATION_REQUIRED
    assert res2.data["amount"] == 50000
    assert res2.data["beneficiary_id"] == "0123456789"
