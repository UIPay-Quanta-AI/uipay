"""
FastAPI Dependency Injection providers for Quanta services, providers, and workflow runners.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.clients.ui_pay.base import UIPayClient
from app.clients.ui_pay.mock import MockUIPayClient
from app.clients.ui_pay.real import RealUIPayClient
from app.core.config import settings
from app.dependencies.tools import build_tool_registry
from app.orchestration.multimodal import MultimodalProcessor
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.voice_pipeline import VoicePipeline
from app.orchestration.workflow_runner import ConversationalWorkflowRunner
from app.providers.asr.factory import get_asr_provider
from app.providers.llm.factory import get_llm_provider
from app.providers.ocr.factory import get_ocr_provider
from app.providers.speaker.factory import get_speaker_provider
from app.services.budget_service import BudgetService
from app.services.financial_profile_service import FinancialProfileService
from app.services.goal_service import GoalService
from app.services.transaction_intelligence_service import TransactionIntelligenceService
from app.services.voice_enrollment import VoiceEnrollmentService
from app.tools.executor import ToolExecutor
from app.tools.policy import ToolPolicy

# Cache for client instances
_client_instance: UIPayClient | None = None


def get_ui_pay_client() -> UIPayClient:
    global _client_instance
    if _client_instance is None:
        if settings.UIPAY_CLIENT_TYPE == "real":
            _client_instance = RealUIPayClient(
                base_url=settings.UIPAY_BASE_URL,
                service_token=settings.UIPAY_SERVICE_TOKEN,
                timeout=settings.UIPAY_TIMEOUT_SECONDS,
            )
        else:
            _client_instance = MockUIPayClient()
    return _client_instance


def get_financial_profile_service(
    client: Annotated[UIPayClient, Depends(get_ui_pay_client)],
) -> FinancialProfileService:
    return FinancialProfileService(client=client)


def get_goal_service(
    client: Annotated[UIPayClient, Depends(get_ui_pay_client)],
) -> GoalService:
    return GoalService(client=client)


def get_budget_service(
    client: Annotated[UIPayClient, Depends(get_ui_pay_client)],
    profile_service: Annotated[FinancialProfileService, Depends(get_financial_profile_service)],
    goal_service: Annotated[GoalService, Depends(get_goal_service)],
) -> BudgetService:
    return BudgetService(
        client=client,
        profile_service=profile_service,
        goal_service=goal_service,
    )


def get_transaction_intelligence_service(
    client: Annotated[UIPayClient, Depends(get_ui_pay_client)],
) -> TransactionIntelligenceService:
    return TransactionIntelligenceService(client=client)


def get_voice_enrollment_service() -> VoiceEnrollmentService:
    speaker_provider = get_speaker_provider()
    return VoiceEnrollmentService(speaker_provider=speaker_provider)


def get_orchestrator(
    client: Annotated[UIPayClient, Depends(get_ui_pay_client)],
) -> Orchestrator:
    llm_provider = get_llm_provider()
    tool_registry = build_tool_registry(ui_pay_client=client)
    policy_evaluator = ToolPolicy()
    tool_executor = ToolExecutor(registry=tool_registry, policy=policy_evaluator)

    return Orchestrator(
        llm_provider=llm_provider,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
    )


def get_voice_pipeline(
    orchestrator: Annotated[Orchestrator, Depends(get_orchestrator)],
) -> VoicePipeline | None:
    try:
        speaker_provider = get_speaker_provider()
        asr_provider = get_asr_provider()
        return VoicePipeline(
            speaker_provider=speaker_provider,
            asr_provider=asr_provider,
            orchestrator=orchestrator,
        )
    except Exception:  # noqa: BLE001
        return None


def get_multimodal_processor(
    orchestrator: Annotated[Orchestrator, Depends(get_orchestrator)],
    voice_pipeline: Annotated[VoicePipeline | None, Depends(get_voice_pipeline)],
) -> MultimodalProcessor:
    try:
        ocr_provider = get_ocr_provider()
    except Exception:  # noqa: BLE001
        ocr_provider = None
    return MultimodalProcessor(
        orchestrator=orchestrator,
        ocr_provider=ocr_provider,
        voice_pipeline=voice_pipeline,
    )


def get_workflow_runner(
    orchestrator: Annotated[Orchestrator, Depends(get_orchestrator)],
    multimodal_processor: Annotated[MultimodalProcessor, Depends(get_multimodal_processor)],
    voice_pipeline: Annotated[VoicePipeline | None, Depends(get_voice_pipeline)],
    client: Annotated[UIPayClient, Depends(get_ui_pay_client)],
) -> ConversationalWorkflowRunner:
    return ConversationalWorkflowRunner(
        orchestrator=orchestrator,
        multimodal_processor=multimodal_processor,
        voice_pipeline=voice_pipeline,
        ui_pay_client=client,
    )
