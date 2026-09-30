from __future__ import annotations

import json
from typing import Any

from app.core.context import RequestContext
from app.orchestration.state_machine import StateMachine
from app.providers.base import ProviderError
from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
    LLMProvider,
    LLMResponse,
)
from app.schemas.response import QuantaResponse
from app.schemas.states import QuantaState
from app.tools.base import (
    ToolError,
    ToolResult,
)
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry

VALID_RESPONSE_LANGUAGES: set[str] = {"en", "pcm", "ig", "yo", "ha"}

CONFIRMATION_SPEECH_BY_LANGUAGE: dict[str, str] = {
    "en": "Please review and confirm the transfer.",
    "pcm": "Abeg review and confirm this transfer.",
    "ig": "Biko nyochaa ma kwado nnyefe a.",
    "yo": "Jọ̀ọ́ yẹ̀ ẹ́ wò kọ́ o si fọwọ́ sí gbigbe owó yìí.",
    "ha": "Taimaka ka duba kuma ka tabbatar da tura kudin.",
}


def resolve_effective_response_language(
    context: RequestContext,
    llm_response: LLMResponse | None = None,
) -> str:
    """
    Determine the effective language Quanta responds in.

    RequestContext.locale
        = requested / default interaction preference (used as ASR hint).

    response_language
        = language Quanta actually responds in (used by TTS for voice resolution).

    If the LLM provided an explicit response_language in provider_metadata, use it.
    Otherwise, fall back to context.locale (normalized canonical code).
    """
    if llm_response and llm_response.provider_metadata:
        candidate = llm_response.provider_metadata.get("response_language")
        if candidate and isinstance(candidate, str):
            norm = candidate.strip().lower()
            if norm in VALID_RESPONSE_LANGUAGES:
                return norm

    if context.locale and context.locale.strip().lower() in VALID_RESPONSE_LANGUAGES:
        return context.locale.strip().lower()

    return "en"


class OrchestrationError(Exception):
    """Base exception for orchestration failures."""


class MaxToolIterationsError(OrchestrationError):
    """Raised when the LLM exceeds the allowed number of tool iterations."""


class Orchestrator:
    """
    Coordinates LLM reasoning, tool execution, and deterministic
    Quanta state management.

    Claude is treated as an untrusted decision-maker. It may request
    tools, but every requested tool passes through ToolExecutor.

    The orchestrator owns the interaction between:
        LLMProvider
        ToolRegistry
        ToolExecutor
        StateMachine

    It does not directly access the UI Pay backend.
    """

    def __init__(
        self,
        *,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        max_tool_iterations: int = 5,
        system_prompt: str | None = None,
    ) -> None:
        if max_tool_iterations < 1:
            raise ValueError("max_tool_iterations must be at least 1")

        self._llm_provider = llm_provider
        self._tool_registry = tool_registry
        self._tool_executor = tool_executor
        self._max_tool_iterations = max_tool_iterations
        self._system_prompt = system_prompt

    async def process(
        self,
        *,
        context: RequestContext,
        user_input: str,
        initial_state: QuantaState = QuantaState.IDLE,
        messages: list[LLMMessage] | None = None,
        system_prompt: str | None = None,
    ) -> QuantaResponse:
        """
        Process one user interaction.

        The caller supplies trusted RequestContext. User identity is never
        accepted from the user input or LLM arguments.
        """

        if not user_input.strip():
            resp_lang = resolve_effective_response_language(context)
            return QuantaResponse.error_response(
                request_id=context.request_id,
                code="EMPTY_INPUT",
                message="User input cannot be empty.",
                response_language=resp_lang,
            )

        state_machine = StateMachine(
            current_state=initial_state,
        )

        if state_machine.current_state != QuantaState.IDLE:
            resp_lang = resolve_effective_response_language(context)
            return QuantaResponse.error_response(
                request_id=context.request_id,
                code="INVALID_INITIAL_STATE",
                message=("A new orchestration request must begin from the idle state."),
                response_language=resp_lang,
            )

        state_machine.transition(QuantaState.PROCESSING)

        conversation = list(messages or [])
        conversation.append(
            LLMMessage(
                role=LLMMessageRole.USER,
                content=user_input.strip(),
            )
        )

        try:
            response = await self._run_llm_loop(
                context=context,
                conversation=conversation,
                state_machine=state_machine,
                system_prompt=system_prompt,
            )
        except ProviderError as exc:
            return self._provider_error_response(
                context=context,
                error=exc,
            )
        except MaxToolIterationsError:
            resp_lang = resolve_effective_response_language(context)
            return QuantaResponse.error_response(
                request_id=context.request_id,
                code="MAX_TOOL_ITERATIONS",
                message=("The request required too many tool operations."),
                speech_text=("I couldn't complete that request safely."),
                response_language=resp_lang,
            )
        except ToolError as exc:
            resp_lang = resolve_effective_response_language(context)
            return QuantaResponse.error_response(
                request_id=context.request_id,
                code="TOOL_ERROR",
                message=str(exc),
                response_language=resp_lang,
            )
        except Exception as exc:
            raise OrchestrationError("Unexpected orchestration failure.") from exc

        return response

    async def _run_llm_loop(
        self,
        *,
        context: RequestContext,
        conversation: list[LLMMessage],
        state_machine: StateMachine,
        system_prompt: str | None = None,
    ) -> QuantaResponse:
        for _iteration in range(self._max_tool_iterations):
            llm_response = await self._generate(
                conversation=conversation,
                system_prompt=system_prompt,
            )

            if llm_response.tool_calls:
                should_stop = await self._handle_tool_calls(
                    context=context,
                    conversation=conversation,
                    llm_response=llm_response,
                    state_machine=state_machine,
                )

                if should_stop:
                    return self._build_deterministic_response(
                        context=context,
                        conversation=conversation,
                        state_machine=state_machine,
                        llm_response=llm_response,
                    )

                continue

            return self._finalize_llm_response(
                context=context,
                llm_response=llm_response,
                state_machine=state_machine,
            )

        raise MaxToolIterationsError()

    async def _generate(
        self,
        *,
        conversation: list[LLMMessage],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        effective_prompt = system_prompt if system_prompt is not None else self._system_prompt
        return await self._llm_provider.generate(
            messages=conversation,
            system_prompt=effective_prompt,
            tools=self._tool_registry.definitions(),
        )

    async def _handle_tool_calls(
        self,
        *,
        context: RequestContext,
        conversation: list[LLMMessage],
        llm_response: LLMResponse,
        state_machine: StateMachine,
    ) -> bool:
        """
        Execute requested tools and determine whether orchestration should
        continue.

        Returns True when the current interaction has reached a deterministic
        application state that should be returned without another LLM call.
        """

        if llm_response.content or llm_response.tool_calls:
            conversation.append(
                LLMMessage(
                    role=LLMMessageRole.ASSISTANT,
                    content=llm_response.content,
                    tool_calls=llm_response.tool_calls,
                )
            )

        for tool_call in llm_response.tool_calls:
            tool_result = await self._execute_tool_call(
                context=context,
                tool_name=tool_call.name,
                arguments=tool_call.arguments,
                state_machine=state_machine,
            )

            conversation.append(
                self._tool_result_message(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    result=tool_result,
                )
            )

            self._apply_deterministic_state_rules(
                tool_name=tool_call.name,
                result=tool_result,
                state_machine=state_machine,
            )

            if (
                tool_call.name == "prepare_transfer"
                and tool_result.success
                and state_machine.current_state == QuantaState.AWAITING_CONFIRMATION
            ):
                return True

        return False

    async def _execute_tool_call(
        self,
        *,
        context: RequestContext,
        tool_name: str,
        arguments: dict[str, Any],
        state_machine: StateMachine,
    ) -> ToolResult:
        return await self._tool_executor.execute(
            tool_name=tool_name,
            arguments=arguments,
            context=context,
            state=state_machine.current_state,
        )

    @staticmethod
    def _tool_result_message(
        *,
        tool_call_id: str,
        tool_name: str,
        result: ToolResult,
    ) -> LLMMessage:
        return LLMMessage(
            role=LLMMessageRole.TOOL,
            content=json.dumps(
                {
                    "tool_name": tool_name,
                    "success": result.success,
                    "data": result.data,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                },
                separators=(",", ":"),
            ),
            tool_call_id=tool_call_id,
        )

    def _build_deterministic_response(
        self,
        *,
        context: RequestContext,
        conversation: list[LLMMessage],
        state_machine: StateMachine,
        llm_response: LLMResponse | None = None,
    ) -> QuantaResponse:
        resp_lang = resolve_effective_response_language(context, llm_response)

        if state_machine.current_state == QuantaState.AWAITING_CONFIRMATION:
            tool_message = self._get_latest_tool_result(
                conversation=conversation,
                tool_name="prepare_transfer",
            )

            if tool_message is None or tool_message.content is None:
                return QuantaResponse.error_response(
                    request_id=context.request_id,
                    code="MISSING_PREPARATION_RESULT",
                    message=("Transfer preparation completed without a usable result."),
                    response_language=resp_lang,
                )

            payload = json.loads(tool_message.content)
            speech_text = CONFIRMATION_SPEECH_BY_LANGUAGE.get(
                resp_lang, CONFIRMATION_SPEECH_BY_LANGUAGE["en"]
            )

            return QuantaResponse.confirmation_required(
                request_id=context.request_id,
                speech_text=speech_text,
                data=payload.get("data") or {},
                response_language=resp_lang,
            )

        return QuantaResponse.error_response(
            request_id=context.request_id,
            code="UNSUPPORTED_DETERMINISTIC_STATE",
            message=("The orchestration flow reached an unsupported deterministic state."),
            response_language=resp_lang,
        )

    @staticmethod
    def _apply_deterministic_state_rules(
        *,
        tool_name: str,
        result: ToolResult,
        state_machine: StateMachine,
    ) -> None:
        """
        Apply application-owned state transitions.

        Claude does not decide these transitions.
        """

        if not result.success:
            return

        if tool_name == "prepare_transfer":
            state_machine.transition(
                QuantaState.AWAITING_CONFIRMATION,
            )

    @staticmethod
    def _finalize_llm_response(
        *,
        context: RequestContext,
        llm_response: LLMResponse,
        state_machine: StateMachine,
    ) -> QuantaResponse:
        """
        Convert a final LLM response into Quanta's universal response
        contract.

        A plain LLM response means the interaction completed without
        requiring deterministic confirmation/input handling here.
        """
        resp_lang = resolve_effective_response_language(context, llm_response)

        if not llm_response.content:
            return QuantaResponse.error_response(
                request_id=context.request_id,
                code="EMPTY_LLM_RESPONSE",
                message="The AI provider returned an empty response.",
                response_language=resp_lang,
            )

        if state_machine.current_state == QuantaState.PROCESSING:
            state_machine.transition(
                QuantaState.SUCCESS,
            )

        return QuantaResponse.success(
            request_id=context.request_id,
            speech_text=llm_response.content,
            data={
                "finish_reason": llm_response.finish_reason,
            },
            response_language=resp_lang,
        )

    @staticmethod
    def _provider_error_response(
        *,
        context: RequestContext,
        error: ProviderError,
    ) -> QuantaResponse:
        resp_lang = resolve_effective_response_language(context)
        return QuantaResponse.error_response(
            request_id=context.request_id,
            code="PROVIDER_ERROR",
            message="An AI provider failed while processing the request.",
            speech_text=("I'm having trouble processing that right now."),
            response_language=resp_lang,
        )

    @staticmethod
    def _get_latest_tool_result(
        *,
        conversation: list[LLMMessage],
        tool_name: str,
    ) -> LLMMessage | None:
        for message in reversed(conversation):
            if message.role != LLMMessageRole.TOOL or not message.content:
                continue

            try:
                payload = json.loads(message.content)
            except json.JSONDecodeError:
                continue

            if payload.get("tool_name") == tool_name:
                return message

        return None
