from __future__ import annotations

import argparse
import asyncio
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.config import Settings
from app.core.context import RequestContext
from app.orchestration.orchestrator import Orchestrator
from app.providers.llm.base import (
    LLMMessage,
    LLMMessageRole,
    LLMProvider,
    LLMResponse,
    LLMToolCall,
)
from app.providers.llm.claude import ClaudeProvider
from app.providers.llm.groq import GroqProvider
from app.providers.llm.mock import MockLLMProvider
from app.schemas.response import QuantaResponse, ResponseStatus
from app.tools.executor import ToolExecutor
from app.tools.implementations.beneficiary import SearchBeneficiaryTool
from app.tools.implementations.transfer import PrepareTransferTool
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

USER_ID = "user_001"

DEMO_BENEFICIARIES = [
    {
        "id": "ben_001",
        "user_id": USER_ID,
        "nickname": "Mum",
        "account_name": "Amaka Okafor",
        "bank_name": "GTBank",
        "account_number": "0123456789",
    },
    {
        "id": "ben_002",
        "user_id": USER_ID,
        "nickname": "Dad",
        "account_name": "Chinedu Okafor",
        "bank_name": "Access Bank",
        "account_number": "0987654321",
    },
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

QUANTA_SYSTEM_PROMPT = (
    "You are Quanta, the financial assistant inside UI Pay. "
    "UI Pay is a Nigerian payment application. "
    "All monetary amounts are in Nigerian Naira (NGN). "
    "Never use ₹, $, €, or any other currency symbol. "
    "When referring to money, use ₦ or 'naira'. "
    "The currency is application-controlled and must not be inferred from "
    "the user's wording. "
    "When a user asks to send money to a saved beneficiary, first call "
    "search_beneficiary to find them. "
    "Once you have the beneficiary_id and an amount, call prepare_transfer. "
    "prepare_transfer only prepares the transaction — it never executes it. "
    "A prepared transaction requires explicit user confirmation. "
    "Never claim that money was transferred merely because a transfer was prepared."
)


# ---------------------------------------------------------------------------
# Manual-session state
# ---------------------------------------------------------------------------
#
# Production confirmation and conversation state belong to the authenticated
# UI Pay backend session. These in-memory objects exist only so the local
# interactive script can simulate multiple conversational turns.
# ---------------------------------------------------------------------------


@dataclass
class PendingConfirmation:
    reference: str
    beneficiary_id: str
    amount: int
    currency: str
    created_at: datetime
    expires_at: datetime


@dataclass
class ChatSession:
    """Holds all mutable state for one interactive manual session."""

    session_id: str
    conversation: list[LLMMessage] = field(default_factory=list)
    pending_confirmation: PendingConfirmation | None = None

    def invalidate_confirmation(self) -> None:
        """Discard any pending confirmation when a new request arrives."""
        self.pending_confirmation = None


# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------
#
# This responder examines the current conversation and produces the
# appropriate deterministic tool call for the user's actual request.
#
# It inspects the full conversation for beneficiary and
# amount context, not just the latest message. This lets
#
#   "search mum" → found Mum
#   "10k please" → calls prepare_transfer for Mum
#
# work correctly even though the second message alone doesn't name Mum.
# ---------------------------------------------------------------------------


def _extract_amount(text: str) -> int | None:
    """
    Extract a simple naira amount from common manual-test input.

    Supported examples:
        5000
        5,000
        ₦5,000
        5k
        5 k
    """

    normalized = text.lower().replace("₦", "").replace("naira", "")

    match = re.search(r"\b(\d+(?:,\d{3})*)\s*k\b", normalized)

    if match:
        return int(match.group(1).replace(",", "")) * 1_000

    match = re.search(r"\b(\d+(?:,\d{3})*)\b", normalized)

    if match:
        return int(match.group(1).replace(",", ""))

    return None


def _extract_beneficiary_name(text: str) -> str | None:
    """Extract one of the demo beneficiary nicknames from user input."""

    normalized = text.lower()

    if re.search(r"\bmum\b|\bmummy\b|\bmama\b", normalized):
        return "Mum"

    if re.search(r"\bdad\b|\bdaddy\b|\bpapa\b", normalized):
        return "Dad"

    return None


def _latest_user_message(messages: list[LLMMessage]) -> str:
    """Return the most recent user message from the conversation."""

    for message in reversed(messages):
        if message.role == LLMMessageRole.USER and message.content:
            return message.content

    return ""


def _conversation_beneficiary_name(messages: list[LLMMessage]) -> str | None:
    """
    Scan the full conversation for any mention of a demo beneficiary.

    This allows "10k please" after "search mum" to still resolve to Mum.
    """

    for message in reversed(messages):
        if message.content:
            name = _extract_beneficiary_name(message.content)
            if name:
                return name

    return None


def _conversation_amount(messages: list[LLMMessage]) -> int | None:
    """
    Scan the full conversation for the most recent amount mention.

    Allows "send to mum" after "10k please" to resolve the amount.
    """

    for message in reversed(messages):
        if message.content:
            amount = _extract_amount(message.content)
            if amount is not None:
                return amount

    return None


def _conversation_has_tool_result(messages: list[LLMMessage]) -> bool:
    """Determine whether the current LLM turn already contains a tool result."""

    return any(message.role == LLMMessageRole.TOOL for message in messages)


def _conversation_has_beneficiary_result(messages: list[LLMMessage]) -> bool:
    """Determine whether a search_beneficiary tool result is in the conversation."""

    import json

    for message in messages:
        if message.role != LLMMessageRole.TOOL:
            continue
        try:
            payload = json.loads(message.content)
            if payload.get("tool_name") == "search_beneficiary" and payload.get("success"):
                return True
        except (json.JSONDecodeError, AttributeError):
            continue

    return False


def create_mock_provider() -> MockLLMProvider:
    """
    Create a deterministic conversational mock provider.

    The mock recognizes the demo beneficiary names and simple transfer
    amounts. It does not attempt to reproduce natural-language reasoning;
    its purpose is to exercise Quanta's orchestration deterministically.

    Key property: the responder inspects the full conversation history so
    multi-turn flows (search → then send) work correctly.
    """

    def responder(
        messages: list[LLMMessage],
        system_prompt: str | None,
        tools: list[dict[str, Any]] | None,
    ) -> LLMResponse:
        user_input = _latest_user_message(messages)
        normalized_input = user_input.lower()

        # Resolve beneficiary and amount from the full conversation, not
        # just the latest message.
        beneficiary_name = _extract_beneficiary_name(user_input) or _conversation_beneficiary_name(
            messages
        )
        amount = _extract_amount(user_input) or _conversation_amount(messages)

        is_transfer_intent = any(
            keyword in normalized_input for keyword in ("send", "transfer", "pay")
        )

        has_beneficiary_result = _conversation_has_beneficiary_result(messages)

        # After search_beneficiary has returned, if we have enough info
        # for a transfer, call prepare_transfer.
        if has_beneficiary_result and beneficiary_name and amount is not None:
            beneficiary_id = "ben_001" if beneficiary_name == "Mum" else "ben_002"

            return LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id=f"mock_prepare_{uuid4().hex[:8]}",
                        name="prepare_transfer",
                        arguments={
                            "beneficiary_id": beneficiary_id,
                            "amount": amount,
                        },
                    )
                ]
            )

        # Transfer requests first search for the beneficiary.
        if beneficiary_name and (is_transfer_intent or amount is not None):
            return LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id=f"mock_search_{uuid4().hex[:8]}",
                        name="search_beneficiary",
                        arguments={
                            "query": beneficiary_name,
                        },
                    )
                ]
            )

        # Simple beneficiary lookup ("find mum", "search dad", etc.)
        if beneficiary_name and any(
            keyword in normalized_input for keyword in ("find", "search", "look", "who", "show")
        ):
            return LLMResponse(
                tool_calls=[
                    LLMToolCall(
                        id=f"mock_search_{uuid4().hex[:8]}",
                        name="search_beneficiary",
                        arguments={
                            "query": beneficiary_name,
                        },
                    )
                ]
            )

        # Amount-only clarification ("10k please" after no prior context)
        if amount is not None and not beneficiary_name:
            return LLMResponse(
                content=(
                    "Who would you like to send that to? "
                    "I have Mum and Dad in your saved beneficiaries."
                )
            )

        # Beneficiary-only clarification
        if beneficiary_name and amount is None:
            return LLMResponse(content=(f"How much would you like to send to {beneficiary_name}?"))

        return LLMResponse(
            content=(
                "I can help you find a saved beneficiary or prepare "
                "a transfer. Try 'send 5,000 to Mum' or 'find Dad'."
            )
        )

    return MockLLMProvider(
        responder=responder,
    )


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------


def create_provider(
    *,
    provider_name: str,
    settings: Settings,
) -> LLMProvider:
    """
    Select the concrete LLM provider for the manual session.

    The provider is injected into the Orchestrator rather than selected
    inside orchestration logic. This preserves the provider abstraction.
    """

    normalized = provider_name.lower()

    if normalized == "mock":
        return create_mock_provider()

    if normalized == "groq":
        return GroqProvider(settings=settings)

    if normalized == "claude":
        return ClaudeProvider(settings=settings)

    raise ValueError(f"Unsupported provider: {provider_name}")


# ---------------------------------------------------------------------------
# Quanta application wiring
# ---------------------------------------------------------------------------


def create_orchestrator(
    *,
    provider: LLMProvider,
) -> tuple[Orchestrator, MockUIPayClient]:
    """
    Build the Quanta dependency graph used by this manual harness.

    The UI Pay client remains mocked so no real financial system is touched.
    """

    ui_pay = MockUIPayClient(
        beneficiaries=DEMO_BENEFICIARIES,
    )

    registry = ToolRegistry()

    registry.register(
        SearchBeneficiaryTool(
            client=ui_pay,
        )
    )

    registry.register(PrepareTransferTool())

    executor = ToolExecutor(
        registry=registry,
        policy=ToolPolicy(),
    )

    orchestrator = Orchestrator(
        llm_provider=provider,
        tool_registry=registry,
        tool_executor=executor,
        system_prompt=QUANTA_SYSTEM_PROMPT,
    )

    return orchestrator, ui_pay


# ---------------------------------------------------------------------------
# Confirmation helpers
# ---------------------------------------------------------------------------


CONFIRMATION_WORDS = {
    "yes",
    "confirm",
    "confirmed",
    "proceed",
    "go ahead",
    "goahead",
    "approve",
    "approved",
}

CANCELLATION_WORDS = {
    "no",
    "cancel",
    "cancel it",
    "stop",
    "abort",
    "don't",
    "dont",
}


def _normalize_confirmation_input(text: str) -> str:
    """Normalize simple confirmation/cancellation phrases."""

    return re.sub(
        r"\s+",
        " ",
        text.lower().strip(),
    )


def is_confirmation(text: str) -> bool:
    normalized = _normalize_confirmation_input(text)

    return normalized in CONFIRMATION_WORDS


def is_cancellation(text: str) -> bool:
    normalized = _normalize_confirmation_input(text)

    return normalized in CANCELLATION_WORDS


def _find_beneficiary(
    *,
    ui_pay: MockUIPayClient,
    beneficiary_id: str,
) -> dict[str, Any] | None:
    """
    Retrieve the trusted demo beneficiary associated with a prepared transfer.

    The lookup is local to this development harness. In production, this
    information would come from the authoritative UI Pay backend.
    """

    for beneficiary in DEMO_BENEFICIARIES:
        if beneficiary["id"] == beneficiary_id:
            return beneficiary

    return None


def _build_confirmation_data(
    *,
    response: QuantaResponse,
    ui_pay: MockUIPayClient,
) -> PendingConfirmation | None:
    """
    Convert trusted prepare_transfer output into manual-session state.

    Only data returned by the controlled tool is used. The LLM's natural
    language response is never treated as authoritative transaction data.
    """

    if response.data is None:
        return None

    reference = response.data.get("reference")
    beneficiary_id = response.data.get("beneficiary_id")
    amount = response.data.get("amount")
    # currency is always NGN from the tool, but we read it back to verify
    currency = response.data.get("currency", "NGN")

    if not reference or not beneficiary_id or amount is None:
        return None

    beneficiary = _find_beneficiary(
        ui_pay=ui_pay,
        beneficiary_id=beneficiary_id,
    )

    if beneficiary is None:
        return None

    now = datetime.now(UTC)

    return PendingConfirmation(
        reference=str(reference),
        beneficiary_id=str(beneficiary_id),
        amount=int(amount),
        currency=str(currency),
        created_at=now,
        expires_at=now + timedelta(minutes=5),
    )


def display_confirmation_details(
    *,
    pending: PendingConfirmation,
    ui_pay: MockUIPayClient,
) -> None:
    """Display trusted confirmation information for the manual session."""

    beneficiary = _find_beneficiary(
        ui_pay=ui_pay,
        beneficiary_id=pending.beneficiary_id,
    )

    if beneficiary is None:
        return

    print()
    print("Confirmation details:")
    print(f"  Recipient: {beneficiary['account_name']}")
    print(f"  Nickname: {beneficiary['nickname']}")
    print(f"  Bank: {beneficiary['bank_name']}")
    print(f"  Account: {beneficiary['account_number']}")
    print(f"  Amount: ₦{pending.amount:,} ({pending.currency})")
    print(f"  Reference: {pending.reference}")
    print()
    print("  Type 'confirm' to continue or 'cancel' to cancel.")


# ---------------------------------------------------------------------------
# Response display
# ---------------------------------------------------------------------------


def display_response(
    response: QuantaResponse,
) -> None:
    """Display the normalized Quanta response in a human-readable format."""

    print()
    print("Quanta:")

    if response.speech:
        print(response.speech.text)

    if response.ui:
        print(f"\nUI state: {response.ui.type.value}")

    if response.data:
        print("\nData:")
        for key, value in response.data.items():
            print(f"  {key}: {value}")

    if response.error:
        print("\nError:")
        print(f"  Code: {response.error.code}")
        print(f"  Message: {response.error.message}")

    print(f"\nStatus: {response.status.value}")


# ---------------------------------------------------------------------------
# Pending-confirmation handling
# ---------------------------------------------------------------------------


async def handle_pending_confirmation(
    *,
    user_input: str,
    pending: PendingConfirmation,
    ui_pay: MockUIPayClient,
) -> tuple[bool, PendingConfirmation | None]:
    """
    Handle confirmation/cancellation for the current manual session.

    Returns:
        handled:
            Whether the input was consumed as confirmation/cancellation.
        pending:
            Updated pending confirmation, or None when the pending operation
            has been completed/cancelled/expired.

    This does not execute a financial transfer. It only demonstrates the
    boundary that would hand an authorized operation back to UI Pay.
    """

    if datetime.now(UTC) >= pending.expires_at:
        print()
        print("Quanta:")
        print("The pending transfer confirmation has expired.")
        print()
        print("Status: expired")
        return True, None

    if is_cancellation(user_input):
        print()
        print("Quanta:")
        print("The prepared transfer has been cancelled.")
        print()
        print("Status: cancelled")
        return True, None

    if not is_confirmation(user_input):
        return False, pending

    beneficiary = _find_beneficiary(
        ui_pay=ui_pay,
        beneficiary_id=pending.beneficiary_id,
    )

    if beneficiary is None:
        print()
        print("Quanta:")
        print("The prepared beneficiary could no longer be verified.")
        print()
        print("Status: error")
        return True, None

    print()
    print("Quanta:")
    print(
        f"Confirmation received for ₦{pending.amount:,} ({pending.currency}) "
        f"to {beneficiary['account_name']}."
    )
    print()
    print(
        "The transfer is prepared, but this manual Quanta prototype "
        "does not execute financial transactions."
    )
    print("The next production boundary is UI Pay authorization/PIN before execution.")
    print()
    print(f"Prepared reference: {pending.reference}")
    print("Status: authorization_required")

    return True, None


# ---------------------------------------------------------------------------
# Interactive session
# ---------------------------------------------------------------------------


async def run_chat(
    *,
    provider_name: str,
) -> None:
    settings = Settings()

    provider = create_provider(
        provider_name=provider_name,
        settings=settings,
    )

    orchestrator, ui_pay = create_orchestrator(
        provider=provider,
    )

    session = ChatSession(
        session_id=f"manual-{uuid4().hex[:8]}",
    )

    print()
    print("--- Quanta Interactive Chat ---")
    print(f"Provider: {provider_name}")
    print(f"Session: {session.session_id}")
    print()
    print("Available demo beneficiaries:")
    print("  Mum → Amaka Okafor, GTBank, 0123456789")
    print("  Dad → Chinedu Okafor, Access Bank, 0987654321")
    print()
    print("Example inputs:")
    print("  find mum")
    print("  find dad")
    print("  send 5k to mum")
    print("  transfer ₦10,000 to dad")
    print()
    print("After a transfer is prepared:")
    print("  confirm")
    print("  cancel")
    print()
    print("Type 'exit' or 'quit' to exit.")
    print()

    while True:
        try:
            user_input = await asyncio.to_thread(
                input,
                "You: ",
            )
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        user_input = user_input.strip()

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Exiting.")
            return

        # ---------------------------------------------------------------
        # Existing confirmation takes priority.
        # ---------------------------------------------------------------
        #
        # This prevents "yes" from being sent to a fresh Orchestrator
        # request that has no knowledge of the previous confirmation.
        # ---------------------------------------------------------------

        if session.pending_confirmation is not None:
            handled, session.pending_confirmation = await handle_pending_confirmation(
                user_input=user_input,
                pending=session.pending_confirmation,
                ui_pay=ui_pay,
            )

            if handled:
                continue

            # Input was not a confirmation word — fall through to normal
            # orchestration with conversation history intact, but clear the
            # stale pending confirmation (user is correcting / changing request).
            session.pending_confirmation = None

        # ---------------------------------------------------------------
        # Normal orchestration turn.
        # Conversation history is passed and then extended with the new
        # messages so subsequent turns have full context.
        # ---------------------------------------------------------------

        context = RequestContext.create(
            user_id=USER_ID,
            session_id=session.session_id,
            operation="manual_chat",
        )

        try:
            response = await orchestrator.process(
                context=context,
                user_input=user_input,
                messages=list(session.conversation),
            )

            display_response(response)

            # -----------------------------------------------------------
            # Extend session conversation history so the next turn has
            # full context.  The orchestrator appends the user message
            # and all LLM/tool turns to the list it receives, so we can
            # reconstruct those messages from the response.
            # We add the user message here; the orchestrator conversation
            # variable is local, so we rebuild from what we know.
            # Simple approach: append user → assistant turn to history.
            # -----------------------------------------------------------

            session.conversation.append(
                LLMMessage(
                    role=LLMMessageRole.USER,
                    content=user_input,
                )
            )

            if response.speech:
                session.conversation.append(
                    LLMMessage(
                        role=LLMMessageRole.ASSISTANT,
                        content=response.speech.text,
                    )
                )

            # -----------------------------------------------------------
            # Store only a successful prepared transfer as the active
            # manual-session confirmation.
            # -----------------------------------------------------------

            if response.status == ResponseStatus.CONFIRMATION_REQUIRED:
                session.pending_confirmation = _build_confirmation_data(
                    response=response,
                    ui_pay=ui_pay,
                )

                if session.pending_confirmation is None:
                    print()
                    print(
                        "Warning: confirmation was requested, but the "
                        "prepared transfer data could not be reconstructed "
                        "from the trusted response."
                    )
                    continue

                display_confirmation_details(
                    pending=session.pending_confirmation,
                    ui_pay=ui_pay,
                )

        except Exception as exc:  # noqa: BLE001
            print()
            print("Quanta error:")
            print(f"  {type(exc).__name__}: {exc}")
            print()
            print("The manual harness caught the exception so the session can continue.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Interact with the Quanta orchestration layer using a selected LLM provider.")
    )

    parser.add_argument(
        "provider",
        choices=["mock", "groq", "claude"],
        help="LLM provider to use for the manual session.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    asyncio.run(
        run_chat(
            provider_name=args.provider,
        )
    )


if __name__ == "__main__":
    main()
