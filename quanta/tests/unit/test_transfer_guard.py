from __future__ import annotations

from app.orchestration.transfer_guard import TransferContext, TransferGuard
from app.providers.llm.base import LLMResponse, LLMToolCall


def test_transfer_context_update_from_user_input() -> None:
    ctx = TransferContext()
    ctx.update_from_user_input("send 10k to Mum")

    assert ctx.beneficiary_name == "Mum"
    assert ctx.beneficiary_id == "ben_001"
    assert ctx.amount == 10_000
    assert ctx.clarification() is None


def test_transfer_context_missing_beneficiary_clarification() -> None:
    ctx = TransferContext()
    ctx.update_from_user_input("send 10k")

    assert ctx.amount == 10_000
    assert ctx.beneficiary_id is None
    clarification = ctx.clarification()
    assert clarification is not None
    assert "Who would you like to send this to" in clarification


def test_transfer_context_ambiguous_amount_clarification() -> None:
    ctx = TransferContext()
    ctx.update_from_user_input("send 15 to Mum")

    assert ctx.beneficiary_name == "Mum"
    assert ctx.amount is None
    clarification = ctx.clarification()
    assert clarification is not None
    assert "do you mean ₦15 or ₦15,000" in clarification


def test_transfer_guard_overrides_llm_arguments() -> None:
    ctx = TransferContext()
    ctx.update_from_user_input("send 10k to Mum")

    guard = TransferGuard(ctx)

    # LLM outputs wrong beneficiary or wrong amount
    llm_resp = LLMResponse(
        tool_calls=[
            LLMToolCall(
                id="call_123",
                name="prepare_transfer",
                arguments={"beneficiary_id": "wrong_id", "amount": 9999},
            )
        ]
    )

    guarded = guard.enforce(llm_resp)
    assert len(guarded.tool_calls) == 1
    args = guarded.tool_calls[0].arguments
    assert args["beneficiary_id"] == "ben_001"
    assert args["amount"] == 10_000


def test_transfer_guard_blocks_prepare_when_incomplete() -> None:
    ctx = TransferContext()
    ctx.update_from_user_input("send money to Mum")  # Missing amount

    guard = TransferGuard(ctx)
    llm_resp = LLMResponse(
        tool_calls=[
            LLMToolCall(
                id="call_123",
                name="prepare_transfer",
                arguments={"beneficiary_id": "ben_001", "amount": 1000},
            )
        ]
    )

    guarded = guard.enforce(llm_resp)
    # Blocked: returns clarification content instead of tool call
    assert guarded.tool_calls == []
    assert guarded.content is not None
    assert "How much" in guarded.content
