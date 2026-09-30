"""
Layer 3 Real-Integration Smoke Test Module for Quanta -> Real UI Pay Backend Integration.

This test module verifies communication with a live or staging UI Pay backend service.
It is safely skipped by default during normal local/CI unit test execution unless
`REAL_SMOKE_TEST=true` environment variable is explicitly set.

NO REAL MONEY IS EVER TRANSFERRED IN AUTOMATED SMOKE TESTS.
Only safe profile retrieval, goal queries, and account validation endpoints are tested.
"""

from __future__ import annotations

import os

import pytest

from app.clients.ui_pay.real import RealUIPayClient


@pytest.mark.skipif(
    os.getenv("REAL_SMOKE_TEST", "").lower() not in ("true", "1", "yes"),
    reason="Layer 3 real integration smoke test skipped. Set REAL_SMOKE_TEST=true to enable.",
)
@pytest.mark.asyncio
async def test_real_uipay_backend_smoke_integration():
    """Verify live connectivity, identity header propagation, and profile initialization."""
    base_url = os.getenv("UIPAY_BASE_URL", "http://localhost:8001")
    service_token = os.getenv("UIPAY_SERVICE_TOKEN")

    client = RealUIPayClient(
        base_url=base_url,
        service_token=service_token,
        timeout=10.0,
    )

    test_user_id = os.getenv("SMOKE_TEST_USER_ID", "usr_smoke_test_123")

    # 1. Profile retrieval / initialization
    profile = await client.get_or_initialize_financial_profile(user_id=test_user_id)
    assert profile is not None
    assert profile.get("user_id") == test_user_id

    # 2. Read-only goals query
    goals = await client.get_goals(user_id=test_user_id)
    assert isinstance(goals, list)

    # 3. Read-only beneficiary search
    beneficiaries = await client.search_beneficiaries(user_id=test_user_id, query="Mom")
    assert isinstance(beneficiaries, list)
