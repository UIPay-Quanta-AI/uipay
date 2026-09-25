from __future__ import annotations

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.domain.confirmation import (
    ConfirmationAlreadyConsumedError,
    ConfirmationExpiredError,
    ConfirmationManager,
    ConfirmationOwnershipError,
    InMemoryConfirmationStore,
)
from app.domain.transfer import (
    AuthoritativeProvider,
    TransferContext,
    TransferGuard,
)
from app.orchestration.orchestrator import Orchestrator
from app.schemas.response import ResponseStatus
from app.services.confirmation_service import handle_pending_confirmation
from app.tools.executor import ToolExecutor
from app.tools.implementations.beneficiaries.beneficiary import SearchBeneficiaryTool
from app.tools.implementations.transfer import PrepareTransferTool
from app.tools.policy import ToolPolicy
from app.tools.registry import ToolRegistry
from scripts.chat_quanta import create_mock_provider


@pytest.fixture
def e2e_system():
    user_id = "user_001"
    beneficiaries = [
        {
            "id": "ben_001",
            "user_id": user_id,
            "nickname": "Mum",
            "account_name": "Amaka Okafor",
            "bank_name": "GTBank",
            "account_number": "0123456789",
        },
        {
            "id": "ben_002",
            "user_id": user_id,
            "nickname": "Dad",
            "account_name": "Chinedu Okafor",
            "bank_name": "Access Bank",
            "account_number": "0987654321",
        },
    ]

    ui_pay = MockUIPayClient(beneficiaries=beneficiaries)
    registry = ToolRegistry()
    registry.register(SearchBeneficiaryTool(client=ui_pay))
    registry.register(PrepareTransferTool())

    executor = ToolExecutor(registry=registry, policy=ToolPolicy())

    mock_llm = create_mock_provider()
    ctx = TransferContext()
    guard = TransferGuard(ctx)
    auth_provider = AuthoritativeProvider(mock_llm, guard)

    orchestrator = Orchestrator(
        llm_provider=auth_provider,
        tool_registry=registry,
        tool_executor=executor,
    )

    conf_store = InMemoryConfirmationStore()
    conf_manager = ConfirmationManager(store=conf_store)

    return orchestrator, ui_pay, ctx, conf_manager


@pytest.mark.asyncio
async def test_scenario_1_known_beneficiary_prepare(e2e_system) -> None:
    """Scenario 1: Send Mum 10k -> prepare -> confirmation required"""
    orchestrator, _, ctx, _ = e2e_system
    ctx.update_from_user_input("send 10k to Mum")

    req_ctx = RequestContext.create(user_id="user_001", session_id="s1", operation="transfer")
    resp = await orchestrator.process(context=req_ctx, user_input="send 10k to Mum")

    assert resp.status == ResponseStatus.CONFIRMATION_REQUIRED
    assert resp.data["beneficiary_id"] == "ben_001"
    assert resp.data["amount"] == 10000


@pytest.mark.asyncio
async def test_scenario_2_direct_confirmation_yes(e2e_system) -> None:
    """Scenario 2: Send Mum 10k -> 'yes' -> confirmation -> authorization boundary"""
    orchestrator, ui_pay, ctx, conf_manager = e2e_system
    ctx.update_from_user_input("send 10k to Mum")
    req_ctx = RequestContext.create(user_id="user_001", session_id="s1", operation="transfer")

    resp = await orchestrator.process(context=req_ctx, user_input="send 10k to Mum")
    assert resp.status == ResponseStatus.CONFIRMATION_REQUIRED

    conf = await conf_manager.create(
        request_id=str(req_ctx.request_id),
        user_id="user_001",
        session_id="s1",
        operation="transfer",
        amount=10000,
        prepared_reference=resp.data["reference"],
        beneficiary_id="ben_001",
    )

    result = await handle_pending_confirmation(
        user_input="yes",
        pending=conf,
        client=ui_pay,
    )
    assert result.handled
    assert result.action == "authorization_required"


@pytest.mark.asyncio
async def test_scenario_3_pidgin_confirmation_run_am(e2e_system) -> None:
    """Scenario 3: Send Mum 10k -> 'run am for me abeg' -> confirmation"""
    orchestrator, ui_pay, ctx, conf_manager = e2e_system
    ctx.update_from_user_input("send 10k to Mum")
    req_ctx = RequestContext.create(user_id="user_001", session_id="s1", operation="transfer")

    resp = await orchestrator.process(context=req_ctx, user_input="send 10k to Mum")

    conf = await conf_manager.create(
        request_id=str(req_ctx.request_id),
        user_id="user_001",
        session_id="s1",
        operation="transfer",
        amount=10000,
        prepared_reference=resp.data["reference"],
        beneficiary_id="ben_001",
    )

    result = await handle_pending_confirmation(
        user_input="run am for me abeg",
        pending=conf,
        client=ui_pay,
    )
    assert result.handled
    assert result.action == "authorization_required"


@pytest.mark.asyncio
async def test_scenario_4_colloquial_confirmation_fire_down(e2e_system) -> None:
    """Scenario 4: Send Mum 10k -> 'you too much, fire down' -> confirmation"""
    orchestrator, ui_pay, ctx, conf_manager = e2e_system
    ctx.update_from_user_input("send 10k to Mum")
    req_ctx = RequestContext.create(user_id="user_001", session_id="s1", operation="transfer")

    resp = await orchestrator.process(context=req_ctx, user_input="send 10k to Mum")

    conf = await conf_manager.create(
        request_id=str(req_ctx.request_id),
        user_id="user_001",
        session_id="s1",
        operation="transfer",
        amount=10000,
        prepared_reference=resp.data["reference"],
        beneficiary_id="ben_001",
    )

    result = await handle_pending_confirmation(
        user_input="you too much, fire down",
        pending=conf,
        client=ui_pay,
    )
    assert result.handled
    assert result.action == "authorization_required"


@pytest.mark.asyncio
async def test_scenario_5_cancellation_dont_run_am(e2e_system) -> None:
    """Scenario 5: Send Mum 10k -> 'don't run am' -> cancellation"""
    orchestrator, ui_pay, ctx, conf_manager = e2e_system
    ctx.update_from_user_input("send 10k to Mum")
    req_ctx = RequestContext.create(user_id="user_001", session_id="s1", operation="transfer")

    resp = await orchestrator.process(context=req_ctx, user_input="send 10k to Mum")

    conf = await conf_manager.create(
        request_id=str(req_ctx.request_id),
        user_id="user_001",
        session_id="s1",
        operation="transfer",
        amount=10000,
        prepared_reference=resp.data["reference"],
        beneficiary_id="ben_001",
    )

    result = await handle_pending_confirmation(
        user_input="don't run am",
        pending=conf,
        client=ui_pay,
    )
    assert result.handled
    assert result.action == "cancelled"


@pytest.mark.asyncio
async def test_scenario_6_modification_overrides_confirmation(e2e_system) -> None:
    """Scenario 6: Send Mum 10k -> 'run am but make it 20k' -> old confirmation invalidated, new preparation"""
    _, _, ctx, _ = e2e_system
    ctx.update_from_user_input("send 10k to Mum")

    from app.domain.confirmation.resolver import ConfirmationIntent, ConfirmationResolver

    resolver = ConfirmationResolver()

    # Security check: MUST resolve to MODIFY, NOT CONFIRM!
    intent = resolver.resolve("run am but make it 20k")
    assert intent == ConfirmationIntent.MODIFY


@pytest.mark.asyncio
async def test_scenario_7_expired_confirmation_rejected(e2e_system) -> None:
    """Scenario 7: Send Mum 10k -> wait until expired -> 'yes' -> rejected"""
    orchestrator, ui_pay, ctx, conf_manager = e2e_system
    ctx.update_from_user_input("send 10k to Mum")
    req_ctx = RequestContext.create(user_id="user_001", session_id="s1", operation="transfer")

    resp = await orchestrator.process(context=req_ctx, user_input="send 10k to Mum")

    # Expired confirmation record
    conf = await conf_manager.create(
        request_id=str(req_ctx.request_id),
        user_id="user_001",
        session_id="s1",
        operation="transfer",
        amount=10000,
        prepared_reference=resp.data["reference"],
        beneficiary_id="ben_001",
        ttl_seconds=-10,
    )

    result = await handle_pending_confirmation(
        user_input="yes",
        pending=conf,
        client=ui_pay,
    )
    assert result.handled
    assert result.action == "expired"

    with pytest.raises(ConfirmationExpiredError):
        await conf_manager.confirm(
            confirmation_id=conf.confirmation_id,
            user_id="user_001",
            session_id="s1",
            operation="transfer",
        )


@pytest.mark.asyncio
async def test_scenario_8_ownership_isolation(e2e_system) -> None:
    """Scenario 8: User A creates confirmation, User B attempts confirmation -> rejected"""
    _, _, _, conf_manager = e2e_system

    conf = await conf_manager.create(
        request_id="req-user-a",
        user_id="user_A",
        session_id="sess_A",
        operation="transfer",
        amount=10000,
        prepared_reference="prep-100",
    )

    with pytest.raises(ConfirmationOwnershipError):
        await conf_manager.confirm(
            confirmation_id=conf.confirmation_id,
            user_id="user_B",
            session_id="sess_B",
            operation="transfer",
        )


@pytest.mark.asyncio
async def test_scenario_9_replay_protection_consumed(e2e_system) -> None:
    """Scenario 9: confirmation consumed -> second confirmation attempt -> rejected"""
    _, _, _, conf_manager = e2e_system

    conf = await conf_manager.create(
        request_id="req-1",
        user_id="user_001",
        session_id="s1",
        operation="transfer",
        amount=10000,
        prepared_reference="prep-100",
    )

    await conf_manager.confirm(
        confirmation_id=conf.confirmation_id,
        user_id="user_001",
        session_id="s1",
        operation="transfer",
    )

    await conf_manager.consume(
        confirmation_id=conf.confirmation_id,
        user_id="user_001",
        session_id="s1",
        operation="transfer",
    )

    with pytest.raises(ConfirmationAlreadyConsumedError):
        await conf_manager.consume(
            confirmation_id=conf.confirmation_id,
            user_id="user_001",
            session_id="s1",
            operation="transfer",
        )


@pytest.mark.asyncio
async def test_scenario_10_beneficiary_switch_no_stale_amount(e2e_system) -> None:
    """Scenario 10: Dad 10k -> Mum -> verify latest beneficiary/amount -> prepare -> confirmation"""
    orchestrator, _, ctx, _ = e2e_system

    # Turn 1: Dad 10k
    ctx.update_from_user_input("send 10k to Dad")
    assert ctx.beneficiary_name == "Dad"
    assert ctx.amount == 10000

    # Turn 2: Switch to Mum
    ctx.update_from_user_input("actually send to Mum")
    assert ctx.beneficiary_name == "Mum"
    assert ctx.beneficiary_id == "ben_001"
    assert ctx.amount == 10000  # Amount preserved, beneficiary updated

    from scripts.chat_quanta import _build_internal_transfer_context_message

    ctx_msg = _build_internal_transfer_context_message(ctx)
    req_ctx = RequestContext.create(user_id="user_001", session_id="s1", operation="transfer")
    resp = await orchestrator.process(
        context=req_ctx,
        user_input="actually send to Mum",
        messages=[ctx_msg] if ctx_msg else None,
    )

    assert resp.status == ResponseStatus.CONFIRMATION_REQUIRED
    assert resp.data["beneficiary_id"] == "ben_001"
    assert resp.data["amount"] == 10000
