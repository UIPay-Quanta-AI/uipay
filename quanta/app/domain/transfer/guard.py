from __future__ import annotations

import dataclasses
import functools
import inspect
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.context import RequestContext
from app.domain.confirmation.errors import TransferGuardError
from app.domain.transfer.context import TransferContext
from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMToolCall


def _arguments_dict(call: Any) -> dict[str, Any]:
    raw = getattr(call, "arguments", None) or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {}
    return dict(raw)


def _rebuild_tool_call(call: Any, arguments: dict[str, Any]) -> Any:
    try:
        if dataclasses.is_dataclass(call) and not isinstance(call, type):
            return dataclasses.replace(call, arguments=arguments)
        model_copy = getattr(call, "model_copy", None)
        if callable(model_copy):
            return model_copy(update={"arguments": arguments})
    except Exception:  # noqa: BLE001, S110
        pass
    return LLMToolCall(id=call.id, name=call.name, arguments=arguments)


def _rebuild_response(response: Any, tool_calls: list[Any]) -> Any:
    try:
        if dataclasses.is_dataclass(response) and not isinstance(response, type):
            return dataclasses.replace(response, tool_calls=tool_calls)
        model_copy = getattr(response, "model_copy", None)
        if callable(model_copy):
            return model_copy(update={"tool_calls": tool_calls})
    except Exception:  # noqa: BLE001, S110
        pass
    return LLMResponse(content=getattr(response, "content", None), tool_calls=tool_calls)


def _same_amount(candidate: Any, expected: int) -> bool:
    try:
        return int(Decimal(str(candidate))) == expected
    except (InvalidOperation, ValueError):
        return False


class TransferGuard:
    """
    Makes the TransferContext authoritative for financial arguments.

    The LLM still decides *that* a transfer should be prepared. The guard
    decides *which* beneficiary and amount are used.
    NO `assert` statements are used in main application code.
    """

    def __init__(self, context: TransferContext) -> None:
        self.context = context

    def validate_prepare_readiness(self, request_context: RequestContext) -> None:
        """
        Fail-closed readiness check for transfer preparation.
        Raises TransferGuardError if context is incomplete or invalid.
        """
        if not request_context.user_id.strip():
            raise TransferGuardError("Unauthenticated user request.")

        if self.context.beneficiary_id is None:
            raise TransferGuardError("Missing destination beneficiary ID.")

        if self.context.amount is None or self.context.amount <= 0:
            raise TransferGuardError("Invalid or missing transfer amount.")

        if self.context.currency != "NGN":
            raise TransferGuardError(f"Unsupported currency {self.context.currency}.")

    def enforce(self, response: Any) -> Any:
        calls = getattr(response, "tool_calls", None)
        if not calls or not isinstance(calls, (list, tuple)):
            return response

        ctx = self.context
        rewritten: list[Any] = []
        prepared = False
        changed = False

        for call in calls:
            name = getattr(call, "name", None)

            if name == "search_beneficiary":
                new_call = self._enforce_search(call)
            elif name == "prepare_transfer":
                clarification = ctx.clarification()
                if clarification is not None:
                    ctx.audit.append(
                        f"blocked prepare_transfer (incomplete or ambiguous fields): {clarification}"
                    )
                    return LLMResponse(content=clarification)
                if prepared:
                    ctx.audit.append("dropped duplicate prepare_transfer call")
                    changed = True
                    continue
                prepared = True
                new_call = self._enforce_prepare(call)
            else:
                new_call = call

            changed = changed or new_call is not call
            rewritten.append(new_call)

        return _rebuild_response(response, rewritten) if changed else response

    def _enforce_search(self, call: Any) -> Any:
        explicit = self.context.facts.explicit_beneficiary
        arguments = _arguments_dict(call)
        query = arguments.get("query")
        if explicit is None or query is None:
            return call
        if str(query).strip().lower() == explicit.lower():
            return call
        self.context.audit.append(f"rewrote search_beneficiary query {query!r} -> {explicit!r}")
        arguments["query"] = explicit
        return _rebuild_tool_call(call, arguments)

    def _enforce_prepare(self, call: Any) -> Any:
        ctx = self.context
        original = _arguments_dict(call)
        arguments = dict(original)

        if original.get("beneficiary_id") != ctx.beneficiary_id:
            ctx.audit.append(
                f"overrode LLM beneficiary_id {original.get('beneficiary_id')!r} -> {ctx.beneficiary_id!r}"
            )
        arguments["beneficiary_id"] = ctx.beneficiary_id

        # NO assert used in production code! Strict explicit check:
        if ctx.amount is None or ctx.amount <= 0:
            ctx.audit.append("blocked prepare_transfer: amount is missing or invalid")
            return _rebuild_response(
                LLMResponse(content="Please specify a valid transfer amount in Naira."),
                [],
            )

        if not _same_amount(original.get("amount"), ctx.amount):
            ctx.audit.append(f"overrode LLM amount {original.get('amount')!r} -> {ctx.amount!r}")
        arguments["amount"] = ctx.amount

        if "currency" in arguments:
            arguments["currency"] = "NGN"

        if arguments == original:
            return call
        return _rebuild_tool_call(call, arguments)


class AuthoritativeProvider(LLMProvider):
    """Transparent LLM-provider proxy that applies a TransferGuard."""

    def __init__(self, inner: LLMProvider, guard: TransferGuard) -> None:
        self._inner = inner
        self._guard = guard

    async def generate(
        self,
        *,
        messages: list[LLMMessage],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        res = await self._inner.generate(
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
        )
        return self._guard.enforce(res)

    def __getattr__(self, name: str) -> Any:
        if name in {"_inner", "_guard"}:
            raise AttributeError(name)

        attribute = getattr(self._inner, name)
        if not callable(attribute) or inspect.isasyncgenfunction(attribute):
            return attribute

        if inspect.iscoroutinefunction(attribute):

            @functools.wraps(attribute)
            async def guarded_async(*args: Any, **kwargs: Any) -> Any:
                return self._guard.enforce(await attribute(*args, **kwargs))

            return guarded_async

        @functools.wraps(attribute)
        def guarded(*args: Any, **kwargs: Any) -> Any:
            result = attribute(*args, **kwargs)
            if inspect.isawaitable(result):

                async def finish() -> Any:
                    return self._guard.enforce(await result)

                return finish()
            return self._guard.enforce(result)

        return guarded
