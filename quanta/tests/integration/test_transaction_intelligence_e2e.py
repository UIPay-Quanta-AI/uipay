from datetime import date

import pytest

from app.clients.ui_pay.mock import MockUIPayClient
from app.core.context import RequestContext
from app.services.transaction_intelligence_service import TransactionIntelligenceService


@pytest.mark.asyncio
async def test_transaction_intelligence_e2e_detects_multiple_patterns():
    client = MockUIPayClient(
        transactions={
            "user_e2e": [
                # Month 1 - baseline
                {
                    "id": "t1",
                    "amount": 100000,
                    "currency": "NGN",
                    "direction": "INBOUND",
                    "classification": "INCOME",
                    "category": "INCOME",
                    "source_type": "employer",
                    "counterparty_name": "Acme",
                    "status": "COMPLETED",
                    "date": "2026-05-05",
                },
                {
                    "id": "t2",
                    "amount": 20000,
                    "currency": "NGN",
                    "direction": "OUTBOUND",
                    "classification": "EXPENSE",
                    "category": "FOOD",
                    "merchant": {"name": "Cafe"},
                    "status": "COMPLETED",
                    "date": "2026-05-10",
                },
                # Month 2 - similar recurring income, same subscription
                {
                    "id": "t3",
                    "amount": 100000,
                    "currency": "NGN",
                    "direction": "INBOUND",
                    "classification": "INCOME",
                    "category": "INCOME",
                    "source_type": "employer",
                    "counterparty_name": "Acme",
                    "status": "COMPLETED",
                    "date": "2026-06-05",
                },
                {
                    "id": "t4",
                    "amount": 20000,
                    "currency": "NGN",
                    "direction": "OUTBOUND",
                    "classification": "EXPENSE",
                    "category": "FOOD",
                    "merchant": {"name": "Cafe"},
                    "status": "COMPLETED",
                    "date": "2026-06-10",
                },
                {
                    "id": "t5",
                    "amount": 15000,
                    "currency": "NGN",
                    "direction": "OUTBOUND",
                    "classification": "EXPENSE",
                    "category": "SUBSCRIPTIONS",
                    "merchant": {"name": "Net"},
                    "status": "COMPLETED",
                    "date": "2026-06-12",
                },
                # Month 3 - new large healthcare expense appears
                {
                    "id": "t6",
                    "amount": 250000,
                    "currency": "NGN",
                    "direction": "OUTBOUND",
                    "classification": "EXPENSE",
                    "category": "HEALTHCARE",
                    "merchant": {"name": "Clinic"},
                    "status": "COMPLETED",
                    "date": "2026-07-05",
                },
            ]
        }
    )

    service = TransactionIntelligenceService(client=client)
    result = await service.analyze(
        context=RequestContext.create(user_id="user_e2e", session_id="e2e-1", operation="analysis"),
        start_date=date(2026, 5, 1),
        end_date=date(2026, 7, 31),
    )

    # expect a notable change for HEALTHCARE appearing in July
    assert any("HEALTHCARE" in msg or "healthcare" in msg.lower() for msg in result.notable_changes)
    # expect aggregated historical periods length == 3
    assert len(result.historical_periods) == 3

    # Assert numerical correctness
    assert result.income_totals["total_income"] == 200000
    assert result.income_totals["count"] == 2
    assert result.expense_totals["total_expenses"] == 305000
    assert result.expense_totals["count"] == 4

    # Assert category percentages sum to 100%
    cat_pcts = result.expense_totals["category_percentages"]
    assert "healthcare" in cat_pcts
    assert "food" in cat_pcts
    assert "subscriptions" in cat_pcts
    total_pct = sum(cat_pcts.values())
    assert abs(total_pct - 100.0) < 0.1

    # Assert historical averages
    hist_avg = result.trends["historical_averages"]
    assert hist_avg["income"] == 66667  # 200000 / 3 periods rounded
    assert hist_avg["expenses"] == 101667  # 305000 / 3 periods rounded

    # Assert observations and signals
    assert len(result.financial_observations) > 0
    assert len(result.budget_review_signals) > 0
    assert result.budget_review_signals[0]["detected"] is True
    assert result.data_quality["code"] == "OK"
