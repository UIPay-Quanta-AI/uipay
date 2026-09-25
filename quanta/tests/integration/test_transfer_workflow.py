from __future__ import annotations

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.orchestration.orchestrator import Orchestrator
from app.orchestration.transfer_guard import (
    AuthoritativeProvider,
    TransferContext,
    TransferGuard,
)
from app.schemas.response import ResponseStatus
from app.services.confirmation_service import handle_pending_confirmation
from app.tools.executor import ToolExecutor
from app.tools.implementations.beneficiary import SearchBeneficiaryTool
from app.tools.implementations.transfer import PrepareTransferTool
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry
from scripts.chat_quanta import create_mock_provider


@pytest.fixture
def setup_transfer_system():
    user_id = "user_001"
    beneficiaries = [
        {
            "id": "ben_001",
            "user_id": user_id,
            "nickname": "Mum",
            "account_name": "Amaka Okafor",
            "bank_name": "GTBank",
            "account_number": "0123456789",
        }
    ]

    ui_pay = MockUIPayClient(beneficiaries=beneficiaries)
    registry = ToolRegistry()
    registry.register(SearchBeneficiaryTool(client=ui_pay))
    registry.register(PrepareTransferTool())

    executor = ToolExecutor(registry=registry, policy=ToolPolicy())

    # Build mock LLM that triggers search and prepare tools
    mock_provider = create_mock_provider()
    ctx = TransferContext()
    guard = TransferGuard(ctx)
    auth_provider = AuthoritativeProvider(mock_provider, guard)

    orchestrator = Orchestrator(
        llm_provider=auth_provider,
        tool_registry=registry,
        tool_executor=executor,
    )

    return orchestrator, ui_pay, ctx


@pytest.mark.asyncio
async def test_step14_prepare_transfer_reaches_awaiting_confirmation(
    setup_transfer_system,
) -> None:
    orchestrator, _, ctx = setup_transfer_system

    # User input explicitly specifying beneficiary and amount
    ctx.update_from_user_input("send 10k to Mum")

    request_context = RequestContext.create(
        user_id="user_001",
        session_id="session_100",
        operation="transfer",
    )

    response = await orchestrator.process(
        context=request_context,
        user_input="send 10k to Mum",
    )

    assert response.status == ResponseStatus.CONFIRMATION_REQUIRED
    assert response.data is not None
    assert response.data["beneficiary_id"] == "ben_001"
    assert response.data["amount"] == 10000
    assert response.data["currency"] == "NGN"


@pytest.mark.asyncio
async def test_step15_confirmation_workflow_confirm(setup_transfer_system) -> None:
    orchestrator, ui_pay, ctx = setup_transfer_system

    ctx.update_from_user_input("send 10k to Mum")
    request_context = RequestContext.create(
        user_id="user_001",
        session_id="session_100",
        operation="transfer",
    )

    response = await orchestrator.process(
        context=request_context,
        user_input="send 10k to Mum",
    )

    assert response.status == ResponseStatus.CONFIRMATION_REQUIRED

    # Build pending confirmation from trusted tool data
    from datetime import UTC, datetime, timedelta

    from app.schemas.confirmation import PendingConfirmation

    now = datetime.now(UTC)
    pending = PendingConfirmation(
        reference=response.data["reference"],
        beneficiary_id=response.data["beneficiary_id"],
        amount=response.data["amount"],
        currency=response.data["currency"],
        created_at=now,
        expires_at=now + timedelta(minutes=5),
    )

    # Step 15: Confirm transfer -> requires PIN / UI Pay authorization next
    conf_res = await handle_pending_confirmation(
        user_input="bẹ́ẹ̀ni, tẹ́síwájú",  # Yoruba confirmation
        pending=pending,
        client=ui_pay,
    )

    assert conf_res.handled
    assert conf_res.action == "authorization_required"


@pytest.mark.asyncio
async def test_step15_confirmation_workflow_cancel(setup_transfer_system) -> None:
    orchestrator, ui_pay, ctx = setup_transfer_system

    ctx.update_from_user_input("send 10k to Mum")
    request_context = RequestContext.create(
        user_id="user_001",
        session_id="session_100",
        operation="transfer",
    )

    response = await orchestrator.process(
        context=request_context,
        user_input="send 10k to Mum",
    )

    assert response.status == ResponseStatus.CONFIRMATION_REQUIRED

    from datetime import UTC, datetime, timedelta

    from app.schemas.confirmation import PendingConfirmation

    now = datetime.now(UTC)
    pending = PendingConfirmation(
        reference=response.data["reference"],
        beneficiary_id=response.data["beneficiary_id"],
        amount=response.data["amount"],
        currency=response.data["currency"],
        created_at=now,
        expires_at=now + timedelta(minutes=5),
    )

    # Step 15: Cancel transfer
    conf_res = await handle_pending_confirmation(
        user_input="no, cancel am",  # Pidgin cancellation
        pending=pending,
        client=ui_pay,
    )

    assert conf_res.handled
    assert conf_res.action == "cancelled"
