"""
HTTP Contract and Resilience Tests for RealUIPayClient.
Validates HTTP transport, header correlation, status error mappings, non-retrying write policies,
and singleton FinancialProfile initialization.
"""

from __future__ import annotations

import httpx
import pytest

from app.clients.ui_pay import (
    RealUIPayClient,
    UIPayAuthError,
    UIPayNotFoundError,
    UIPayServerError,
    UIPayValidationError,
)


@pytest.mark.asyncio
async def test_get_or_initialize_profile_creates_default_when_missing():
    requests_made: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        requests_made.append(request)
        if request.method == "GET":
            return httpx.Response(404, json={"detail": "Not found"})
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "user_id": "usr_init_1",
                    "monthly_income": "0.00",
                    "currency": "NGN",
                },
            )
        return httpx.Response(400)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        uipay = RealUIPayClient(base_url="http://testserver", http_client=client)
        profile = await uipay.get_or_initialize_financial_profile(user_id="usr_init_1")

    assert profile["user_id"] == "usr_init_1"
    assert profile["monthly_income"] == "0.00"
    assert len(requests_made) == 2
    assert requests_made[0].method == "GET"
    assert requests_made[1].method == "POST"


@pytest.mark.asyncio
async def test_get_or_initialize_profile_returns_existing():
    requests_made: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        requests_made.append(request)
        return httpx.Response(
            200,
            json={
                "user_id": "usr_exist_1",
                "monthly_income": "500000.00",
                "currency": "NGN",
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        uipay = RealUIPayClient(base_url="http://testserver", http_client=client)
        profile = await uipay.get_or_initialize_financial_profile(user_id="usr_exist_1")

    assert profile["monthly_income"] == "500000.00"
    assert len(requests_made) == 1
    assert requests_made[0].method == "GET"


@pytest.mark.asyncio
async def test_get_or_initialize_profile_concurrency_race():
    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if request.method == "GET" and call_count == 1:
            return httpx.Response(404)
        if request.method == "POST":
            return httpx.Response(409, json={"detail": "Conflict"})
        if request.method == "GET" and call_count == 3:
            return httpx.Response(200, json={"user_id": "usr_race", "monthly_income": "200000.00"})
        return httpx.Response(500)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        uipay = RealUIPayClient(base_url="http://testserver", http_client=client)
        profile = await uipay.get_or_initialize_financial_profile(user_id="usr_race")

    assert profile["user_id"] == "usr_race"
    assert call_count == 3


@pytest.mark.asyncio
async def test_non_retryable_financial_write_policy():
    """Verify POST operations fail fast on 500 without retrying to prevent duplicate mutations."""
    attempts = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, json={"detail": "Internal Error"})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        uipay = RealUIPayClient(base_url="http://testserver", max_retries=2, http_client=client)

        with pytest.raises(UIPayServerError):
            await uipay.create_goal(
                user_id="usr1",
                goal_data={"name": "Test Goal", "target_amount": "10000.00"},
            )

    assert attempts == 1  # Exactly 1 attempt made for write operation


@pytest.mark.asyncio
async def test_retryable_read_policy():
    """Verify GET operations automatically retry on transient 500 errors."""
    attempts = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500)
        return httpx.Response(200, json=[{"id": "goal1"}])

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        uipay = RealUIPayClient(base_url="http://testserver", max_retries=2, http_client=client)
        goals = await uipay.get_goals(user_id="usr1")

    assert len(goals) == 1
    assert attempts == 2


@pytest.mark.asyncio
async def test_status_error_mappings():
    statuses_and_errors = [
        (401, UIPayAuthError),
        (404, UIPayNotFoundError),
        (422, UIPayValidationError),
        (503, UIPayServerError),
    ]

    for status_code, expected_exc in statuses_and_errors:

        def mock_handler(request: httpx.Request, code: int = status_code) -> httpx.Response:
            return httpx.Response(code, json={"detail": "Error"})

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            uipay = RealUIPayClient(base_url="http://testserver", max_retries=0, http_client=client)
            with pytest.raises(expected_exc):
                await uipay.get_financial_profile(user_id="usr_err")


@pytest.mark.asyncio
async def test_correlation_header_propagation():
    last_headers: dict[str, str] = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal last_headers
        last_headers = dict(request.headers)
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        uipay = RealUIPayClient(
            base_url="http://testserver", service_token="secret_token", http_client=client
        )
        await uipay._request(
            "GET",
            "/api/v1/users/usr1/goals",
            request_id="req-corr-1234",
            is_retryable=True,
        )

    assert last_headers.get("x-request-id") == "req-corr-1234"
    assert last_headers.get("x-correlation-id") == "req-corr-1234"
    assert last_headers.get("authorization") == "Bearer secret_token"
