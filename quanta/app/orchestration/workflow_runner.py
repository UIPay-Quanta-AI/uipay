"""
Conversational Workflow Runner coordinating multi-turn interactions, state memory, and domain lifecycles.
"""

from __future__ import annotations

from app.clients.ui_pay.base import UIPayClient
from app.core.context import RequestContext
from app.domain.conversational.session import SessionManager, SessionState
from app.orchestration.multimodal import (
    MultimodalInput,
    MultimodalOutcome,
    MultimodalProcessor,
    MultimodalResult,
)
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.voice_pipeline import (
    VoicePipeline,
    VoicePipelineOutcome,
    VoicePipelineResult,
)
from app.prompts.builder import build_quanta_system_prompt
from app.schemas.response import QuantaResponse, ResponseStatus, UIType


class ConversationalWorkflowRunner:
    """
    Coordinates multi-turn conversational workflows across Quanta services,
    preserving session context and state invariants.
    """

    def __init__(
        self,
        *,
        orchestrator: Orchestrator,
        multimodal_processor: MultimodalProcessor,
        voice_pipeline: VoicePipeline | None = None,
        ui_pay_client: UIPayClient | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._multimodal_processor = multimodal_processor
        self._voice_pipeline = voice_pipeline
        self._ui_pay_client = ui_pay_client
        self._session_manager = session_manager or SessionManager.get_instance()

    async def run_interaction(
        self,
        *,
        context: RequestContext,
        input_data: MultimodalInput,
    ) -> QuantaResponse:
        """
        Process a single conversational turn across text, image, voice, or multimodal modalities.
        """
        session = self._session_manager.get_session(
            session_id=context.session_id,
            user_id=context.user_id,
        )

        # 1. Inspect user input text & extracted modality data
        user_text = (input_data.text or "").strip()

        # Check if user is responding to an active transfer partial information question
        if (
            session.active_workflow == "TRANSFER"
            and session.collected_data.get("bank")
            and session.collected_data.get("account_number")
            and not session.collected_data.get("amount")
            and user_text
        ):
            # Augment user text with active partial transfer context
            partial_bank = session.collected_data["bank"]
            partial_account = session.collected_data["account_number"]
            partial_recipient = session.collected_data.get("recipient_name", "")

            augmented_text = (
                f"Transfer {user_text} to account {partial_account} at {partial_bank} "
                f"({partial_recipient})."
            )
            input_data.text = augmented_text

        # 2. Build dynamic system prompt incorporating session state & safety guidelines
        system_prompt = build_quanta_system_prompt(
            context=context,
            active_workflow=session.active_workflow,
            session_data=session.collected_data if session.collected_data else None,
        )

        # 3. Process input via MultimodalProcessor
        result: MultimodalResult = await self._multimodal_processor.process(
            context=context,
            input_data=input_data,
            messages=session.messages if session.messages else None,
            system_prompt=system_prompt,
        )

        if result.outcome != MultimodalOutcome.SUCCESS or result.response is None:
            return result.response or QuantaResponse.error_response(
                request_id=context.request_id,
                code="MULTIMODAL_FAILURE",
                message=result.error or "Multimodal interaction failed.",
                response_language=context.locale,
            )

        response = result.response

        # 4. Post-process response to manage workflow state & conversation continuity
        self._update_session_state(session=session, response=response, user_text=user_text)

        return response

    async def run_voice_turn(
        self,
        *,
        context: RequestContext,
        audio: bytes,
        voice_profile: bytes | None,
        verification_threshold: float | None = None,
        filename: str | None = None,
    ) -> VoicePipelineResult:
        """
        Process a voice turn through VoicePipeline (verification -> ASR -> Orchestration).
        """
        if self._voice_pipeline is None:
            return VoicePipelineResult(
                outcome=VoicePipelineOutcome.TRANSCRIPTION_FAILED,
                error="Voice pipeline is not configured.",
                response=QuantaResponse.error_response(
                    request_id=context.request_id,
                    code="VOICE_PIPELINE_UNAVAILABLE",
                    message="Voice pipeline is not configured.",
                    response_language=context.locale,
                ),
            )

        session = self._session_manager.get_session(
            session_id=context.session_id,
            user_id=context.user_id,
        )

        pipe_res = await self._voice_pipeline.process(
            context=context,
            audio=audio,
            voice_profile=voice_profile,
            messages=session.messages if session.messages else None,
            language=context.locale,
            verification_threshold=verification_threshold,
            filename=filename,
        )

        if pipe_res.outcome == VoicePipelineOutcome.SUCCESS and pipe_res.response:
            asr_text = pipe_res.transcript.text if pipe_res.transcript else ""
            self._update_session_state(
                session=session, response=pipe_res.response, user_text=asr_text
            )

        return pipe_res

    def _update_session_state(
        self,
        *,
        session: SessionState,
        response: QuantaResponse,
        user_text: str,
    ) -> None:
        """
        Track active session state transitions based on response & output data.
        """
        if response.status == ResponseStatus.CONFIRMATION_REQUIRED and response.data:
            # Transfer confirmation state reached
            session.active_workflow = "TRANSFER"
            session.last_transfer_candidate = dict(response.data)
            session.collected_data = dict(response.data)
        elif (
            response.status == ResponseStatus.INPUT_REQUIRED
            and response.ui.type == UIType.ACCOUNT_INPUT
        ):
            # Partial transfer state waiting for amount or recipient
            session.active_workflow = "TRANSFER"
            if response.data:
                session.collected_data.update(response.data)
        elif response.status == ResponseStatus.SUCCESS:
            if response.ui.type == UIType.BUDGET:
                session.reset_workflow()
            elif session.active_workflow == "TRANSFER":
                # Transfer completed/confirmed
                session.reset_workflow()

        session.update_timestamp()
