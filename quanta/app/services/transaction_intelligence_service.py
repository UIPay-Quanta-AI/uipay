from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.clients.ui_pay.base import UIPayClient
from app.core.config import settings
from app.core.context import RequestContext
from app.domain.budget.models import TransactionBudgetContext
from app.domain.transaction_intelligence.enums import (
    CounterpartyType,
    DataQualityCode,
    FinancialClassification,
    TrendType,
)
from app.domain.transaction_intelligence.models import (
    BudgetReviewSignal,
    FinancialObservation,
    NormalizedTransaction,
    TransactionIntelligenceResult,
)
from app.domain.transaction_intelligence.rules import (
    classify_trend,
    determine_classification,
    determine_direction,
    infer_category,
    is_included_status,
    map_status,
    resolve_counterparty_type,
)


class TransactionIntelligenceServiceError(Exception):
    """Service-level error for transaction intelligence failures."""


class TransactionIntelligenceService:
    """Deterministic transaction intelligence service for UI Pay transaction data."""

    MAX_LOOKBACK_DAYS = getattr(settings, "TRANSACTION_MAX_LOOKBACK_DAYS", 365)
    SIGNIFICANT_CHANGE_PERCENT = Decimal(
        str(getattr(settings, "TRANSACTION_SIGNIFICANT_CHANGE_PERCENT", "0.20"))
    )
    MINIMUM_ABSOLUTE_CHANGE = Decimal(
        str(getattr(settings, "TRANSACTION_MINIMUM_ABSOLUTE_CHANGE", "10000.00"))
    )
    MINIMUM_OBSERVATION_PERIODS = getattr(settings, "TRANSACTION_MINIMUM_OBSERVATION_PERIODS", 2)

    def __init__(self, *, client: UIPayClient) -> None:
        self._client = client

    async def analyze(
        self,
        *,
        context: RequestContext,
        start_date: date,
        end_date: date,
    ) -> TransactionIntelligenceResult:
        """
        Analyze transaction history for the authenticated user context.
        Identity context comes authoritatively from RequestContext.user_id.
        """
        resolved_user_id = (context.user_id or "").strip()
        if not resolved_user_id:
            raise TransactionIntelligenceServiceError("User identity context is required.")

        if start_date > end_date:
            raise TransactionIntelligenceServiceError("start_date must be on or before end_date.")

        effective_start, effective_end = self._resolve_lookback(start_date, end_date)

        try:
            raw_transactions = await self._client.get_transactions(
                user_id=resolved_user_id,
                start_date=effective_start,
                end_date=effective_end,
            )
        except Exception as exc:
            raise TransactionIntelligenceServiceError(
                f"UI Pay transaction provider failed: {exc}"
            ) from exc

        normalized: list[NormalizedTransaction] = []
        invalid_count = 0
        invalid_ids: list[str] = []

        for raw in raw_transactions:
            try:
                tx = self._normalize_transaction(raw)
                normalized.append(tx)
            except Exception:  # noqa: BLE001
                invalid_count += 1
                try:
                    invalid_ids.append(str(raw.get("id") or raw.get("reference") or "unknown"))
                except Exception:  # noqa: BLE001
                    invalid_ids.append("unknown")

        filtered = [tx for tx in normalized if is_included_status(tx.status)]

        if not filtered:
            tx_context = TransactionBudgetContext(
                data_available=False,
                lookback_period={
                    "start_date": effective_start.isoformat(),
                    "end_date": effective_end.isoformat(),
                },
                historical_periods=[],
                trends={
                    "income_trend": TrendType.INSUFFICIENT_DATA.value,
                    "expense_trend": TrendType.INSUFFICIENT_DATA.value,
                },
                notable_changes=[],
            )
            return TransactionIntelligenceResult(
                data_available=False,
                lookback_period={
                    "start_date": effective_start.isoformat(),
                    "end_date": effective_end.isoformat(),
                },
                normalized_transactions=[],
                historical_periods=[],
                trends={
                    "income_trend": TrendType.INSUFFICIENT_DATA.value,
                    "expense_trend": TrendType.INSUFFICIENT_DATA.value,
                },
                notable_changes=[],
                budget_review_signals=[],
                income_totals={"total_income": 0, "count": 0},
                expense_totals={"total_expenses": 0, "count": 0},
                transaction_budget_context=tx_context,
                invalid_transactions_count=invalid_count,
                data_quality={
                    "code": DataQualityCode.NO_DATA.value,
                    "invalid_count": invalid_count,
                    "invalid_transaction_ids": invalid_ids,
                },
            )

        income_rows = [tx for tx in filtered if tx.classification == FinancialClassification.INCOME]
        expense_rows = [
            tx for tx in filtered if tx.classification == FinancialClassification.EXPENSE
        ]

        income_recurring_sources = self._identify_recurring_sources(
            income_rows,
            classification=FinancialClassification.INCOME,
        )
        expense_recurring_sources = self._identify_recurring_sources(
            expense_rows,
            classification=FinancialClassification.EXPENSE,
        )

        periods = self._build_periods(
            filtered,
            effective_start,
            effective_end,
            income_recurring_sources=income_recurring_sources,
            expense_recurring_sources=expense_recurring_sources,
        )

        income_total = sum((tx.amount for tx in income_rows), Decimal("0.00"))
        expense_total = sum((tx.amount for tx in expense_rows), Decimal("0.00"))

        income_trend = self._classify_trend([p["observed_income"] for p in periods])
        expense_trend = self._classify_trend([p["observed_expenses"] for p in periods])
        income_variability = self._income_variability(periods)
        income_variability_label = self._income_variability_label(income_variability, len(periods))

        expense_category_percentages = self._category_percentages(expense_rows)
        category_trends = self._category_trends(periods)

        hist_avg_income = (
            int(self._average_amount([Decimal(str(p.get("observed_income", 0))) for p in periods]))
            if periods
            else 0
        )
        hist_avg_expense = (
            int(
                self._average_amount([Decimal(str(p.get("observed_expenses", 0))) for p in periods])
            )
            if periods
            else 0
        )
        category_hist_averages = self._category_historical_averages(periods)
        latest_vs_previous, latest_vs_average = self._build_period_comparisons(
            periods, category_hist_averages
        )

        notable_changes, change_observations = self._detect_significant_changes(
            periods,
            expense_recurring_sources=expense_recurring_sources,
            income_recurring_sources=income_recurring_sources,
        )

        financial_observations = self._build_all_financial_observations(
            periods,
            category_hist_averages,
            change_observations,
            income_variability=income_variability,
            income_variability_label=income_variability_label,
            expense_recurring_sources=expense_recurring_sources,
            income_recurring_sources=income_recurring_sources,
        )

        budget_review_signals = self._build_budget_review_signals_from_observations(
            change_observations
        )

        trends_summary = {
            "income_trend": income_trend,
            "expense_trend": expense_trend,
            "income_variability": income_variability,
            "income_variability_label": income_variability_label,
            "category_trends": category_trends,
            "category_percentages": expense_category_percentages,
            "category_historical_averages": category_hist_averages,
            "historical_averages": {
                "income": hist_avg_income,
                "expenses": hist_avg_expense,
            },
            "latest_vs_previous": latest_vs_previous,
            "latest_vs_average": latest_vs_average,
        }

        tx_context = TransactionBudgetContext(
            data_available=True,
            lookback_period={
                "start_date": effective_start.isoformat(),
                "end_date": effective_end.isoformat(),
            },
            historical_periods=periods,
            trends=trends_summary,
            notable_changes=list(notable_changes),
        )

        data_quality: dict[str, Any] = {"code": DataQualityCode.OK.value}
        if invalid_count > 0:
            data_quality = {
                "code": DataQualityCode.INVALID_DATA_PRESENT.value,
                "invalid_count": invalid_count,
                "invalid_transaction_ids": invalid_ids,
            }
        if len(periods) < max(1, self.MINIMUM_OBSERVATION_PERIODS):
            data_quality = {
                "code": DataQualityCode.INSUFFICIENT_HISTORY.value,
                "periods_observed": len(periods),
            }

        return TransactionIntelligenceResult(
            data_available=True,
            lookback_period={
                "start_date": effective_start.isoformat(),
                "end_date": effective_end.isoformat(),
            },
            normalized_transactions=filtered,
            historical_periods=periods,
            trends=trends_summary,
            notable_changes=notable_changes,
            financial_observations=financial_observations,
            budget_review_signals=budget_review_signals,
            income_totals={
                "total_income": int(income_total),
                "count": len(income_rows),
                "historical_average": hist_avg_income,
                "variability": income_variability,
                "variability_label": income_variability_label,
            },
            expense_totals={
                "total_expenses": int(expense_total),
                "count": len(expense_rows),
                "category_totals": self._category_totals(expense_rows),
                "category_percentages": expense_category_percentages,
                "category_historical_averages": category_hist_averages,
                "historical_average": hist_avg_expense,
            },
            transaction_budget_context=tx_context,
            invalid_transactions_count=invalid_count,
            data_quality=data_quality,
        )

    def _resolve_lookback(self, start_date: date, end_date: date) -> tuple[date, date]:
        delta_days = (end_date - start_date).days
        if delta_days > self.MAX_LOOKBACK_DAYS:
            return end_date - timedelta(days=self.MAX_LOOKBACK_DAYS), end_date
        return start_date, end_date

    def _normalize_transaction(self, raw: dict[str, Any]) -> NormalizedTransaction:
        if not isinstance(raw, dict):
            raise TypeError("Transaction raw payload must be a dictionary.")

        raw_id = raw.get("id") or raw.get("reference")
        if not raw_id:
            raise ValueError("Transaction must have an id or reference.")

        amount_val = raw.get("amount")
        if amount_val is None:
            raise ValueError("Transaction amount is required.")
        raw_amount = Decimal(str(amount_val))
        amount = abs(raw_amount)

        raw_status = str(raw.get("status", "COMPLETED"))
        status = map_status(raw_status)

        raw_direction = str(raw.get("direction") or "")
        direction = determine_direction(raw_direction, raw_amount)

        raw_classification = str(raw.get("classification") or "")
        classification = determine_classification(raw_classification, direction, raw)

        category = str(raw.get("category") or infer_category(raw, classification)).strip().upper()
        if not category:
            category = "UNKNOWN"

        counterparty_type = resolve_counterparty_type(raw, direction, classification)
        counterparty_name = self._extract_counterparty_name(raw, counterparty_type)

        merchant = None
        beneficiary = None
        if counterparty_type == CounterpartyType.MERCHANT:
            merchant_name = raw.get("merchant_name") or raw.get("merchant")
            if isinstance(merchant_name, dict):
                merchant = dict(merchant_name)
            elif merchant_name:
                merchant = {"name": str(merchant_name)}
        elif counterparty_type == CounterpartyType.BENEFICIARY:
            beneficiary_name = raw.get("beneficiary_name") or raw.get("beneficiary")
            if isinstance(beneficiary_name, dict):
                beneficiary = dict(beneficiary_name)
            elif beneficiary_name:
                beneficiary = {"name": str(beneficiary_name)}

        date_value = raw.get("date")
        if isinstance(date_value, str):
            tx_date = date.fromisoformat(date_value)
        elif isinstance(date_value, date):
            tx_date = date_value
        else:
            raise TypeError("Transaction date is required and must be a valid date.")

        reference = raw.get("reference") or raw.get("id")

        return NormalizedTransaction(
            id=str(raw_id),
            reference=str(reference) if reference is not None else None,
            amount=amount,
            currency=str(raw.get("currency", "NGN")).upper(),
            direction=direction,
            classification=classification,
            category=category,
            counterparty_type=counterparty_type,
            counterparty_name=counterparty_name,
            merchant=merchant,
            beneficiary=beneficiary,
            status=status,
            description=str(raw.get("description") or "").strip() or None,
            date=tx_date,
            source_data=dict(raw),
        )

    def _extract_counterparty_name(
        self,
        raw: dict[str, Any],
        counterparty_type: CounterpartyType,
    ) -> str | None:
        for key in [
            "counterparty_name",
            "employer_name",
            "merchant_name",
            "beneficiary_name",
            "source_name",
            "name",
        ]:
            value = raw.get(key)
            if value:
                if isinstance(value, dict):
                    return (
                        str(
                            value.get("name")
                            or value.get("merchant_name")
                            or value.get("beneficiary_name")
                            or ""
                        ).strip()
                        or None
                    )
                return str(value).strip() or None

        if counterparty_type == CounterpartyType.MERCHANT:
            merchant_val = raw.get("merchant")
            if isinstance(merchant_val, dict):
                return str(merchant_val.get("name") or "").strip() or None
            if isinstance(merchant_val, str):
                return merchant_val.strip() or None

        if counterparty_type == CounterpartyType.BENEFICIARY:
            beneficiary_val = raw.get("beneficiary")
            if isinstance(beneficiary_val, dict):
                return str(beneficiary_val.get("name") or "").strip() or None
            if isinstance(beneficiary_val, str):
                return beneficiary_val.strip() or None

        return None

    def _build_periods(
        self,
        normalized: list[NormalizedTransaction],
        start_date: date,
        end_date: date,
        income_recurring_sources: set[str] | None = None,
        expense_recurring_sources: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        periods: list[dict[str, Any]] = []

        if income_recurring_sources is None:
            income_recurring_sources = self._identify_recurring_sources(
                [tx for tx in normalized if tx.classification == FinancialClassification.INCOME],
                classification=FinancialClassification.INCOME,
            )
        if expense_recurring_sources is None:
            expense_recurring_sources = self._identify_recurring_sources(
                [tx for tx in normalized if tx.classification == FinancialClassification.EXPENSE],
                classification=FinancialClassification.EXPENSE,
            )

        month_cursor = date(start_date.year, start_date.month, 1)
        end_month = date(end_date.year, end_date.month, 1)

        while month_cursor <= end_month:
            next_month = (month_cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_end = min(end_date, next_month - timedelta(days=1))

            month_transactions = [tx for tx in normalized if month_cursor <= tx.date <= month_end]

            income_total = sum(
                (
                    tx.amount
                    for tx in month_transactions
                    if tx.classification == FinancialClassification.INCOME
                ),
                Decimal("0.00"),
            )
            recurring_income_total = sum(
                (
                    tx.amount
                    for tx in month_transactions
                    if tx.classification == FinancialClassification.INCOME
                    and self._recurring_key(tx, FinancialClassification.INCOME)
                    in income_recurring_sources
                ),
                Decimal("0.00"),
            )

            expense_total = sum(
                (
                    tx.amount
                    for tx in month_transactions
                    if tx.classification == FinancialClassification.EXPENSE
                ),
                Decimal("0.00"),
            )
            recurring_expense_total = Decimal("0.00")
            recurring_expense_keys: set[str] = set()

            for tx in month_transactions:
                if (
                    tx.classification == FinancialClassification.EXPENSE
                    and self._recurring_key(tx, FinancialClassification.EXPENSE)
                    in expense_recurring_sources
                ):
                    recurring_expense_total += tx.amount
                    recurring_expense_keys.add(
                        self._recurring_key(tx, FinancialClassification.EXPENSE)
                    )

            category_totals: dict[str, Decimal] = defaultdict(Decimal)
            for tx in month_transactions:
                if tx.classification == FinancialClassification.EXPENSE:
                    category_totals[tx.category.lower()] += tx.amount

            period = {
                "period": month_cursor.strftime("%Y-%m"),
                "observed_income": int(income_total),
                "recurring_income": int(recurring_income_total),
                "observed_expenses": int(expense_total),
                "spending_by_category": {k: int(v) for k, v in sorted(category_totals.items())},
                "recurring_expense_total": int(recurring_expense_total),
                "recurring_expense_keys": sorted(recurring_expense_keys),
                "recurring_expenses": [
                    {
                        "category": tx.category,
                        "amount": int(tx.amount),
                        "counterparty": tx.counterparty_name
                        or (tx.merchant.get("name") if tx.merchant else None),
                        "recurring_key": self._recurring_key(tx, FinancialClassification.EXPENSE),
                    }
                    for tx in month_transactions
                    if tx.classification == FinancialClassification.EXPENSE
                    and self._recurring_key(tx, FinancialClassification.EXPENSE)
                    in expense_recurring_sources
                ],
                "notable_changes": [],
            }
            periods.append(period)

            # MUST increment month_cursor to prevent infinite loop!
            month_cursor = next_month

        return periods

    def _classify_trend(self, values: list[int | float | Decimal]) -> str:
        return classify_trend(values).value

    def _category_percentages(self, rows: list[NormalizedTransaction]) -> dict[str, float]:
        totals = self._category_totals(rows)
        total_expenses = sum((Decimal(str(v)) for v in totals.values()), Decimal("0.00"))
        if total_expenses == Decimal(0):
            return {key: 0.0 for key in totals}
        return {
            key: float(
                ((Decimal(str(value)) / total_expenses) * Decimal(100)).quantize(Decimal("0.01"))
            )
            for key, value in totals.items()
        }

    def _category_totals(self, rows: list[NormalizedTransaction]) -> dict[str, int]:
        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for tx in rows:
            if tx.classification == FinancialClassification.EXPENSE:
                totals[tx.category.lower()] += tx.amount
        return {k: int(v) for k, v in totals.items()}

    def _average_amount(self, values: list[Any]) -> Decimal:
        vals = [Decimal(str(v)) for v in values if v is not None]
        if not vals:
            return Decimal(0)
        total = sum(vals, Decimal(0))
        return (total / Decimal(len(vals))).quantize(Decimal(1))

    def _income_variability(self, periods: list[dict[str, Any]]) -> float:
        incomes = [
            Decimal(str(p.get("observed_income", 0)))
            for p in periods
            if p.get("observed_income") is not None
        ]
        if not incomes:
            return 0.0
        mean = sum(incomes, Decimal(0)) / Decimal(len(incomes))
        if mean == Decimal(0):
            return 0.0
        variance = sum([(x - mean) ** 2 for x in incomes], Decimal(0)) / Decimal(len(incomes))
        stddev = variance.sqrt()
        cov = (stddev / mean) * Decimal(100)
        return float(cov.quantize(Decimal("0.01")))

    def _recurring_key(
        self,
        tx: NormalizedTransaction,
        classification: FinancialClassification,
    ) -> str:
        name = (
            tx.counterparty_name
            or (tx.merchant.get("name") if tx.merchant else None)
            or (tx.beneficiary.get("name") if tx.beneficiary else None)
            or (tx.description or "").strip()
            or tx.id
        )
        return name.strip().lower()

    def _identify_recurring_sources(
        self,
        rows: list[NormalizedTransaction],
        *,
        classification: FinancialClassification,
    ) -> set[str]:
        groups: dict[str, list[NormalizedTransaction]] = defaultdict(list)
        for tx in rows:
            key = self._recurring_key(tx, classification)
            if key:
                groups[key].append(tx)

        recurring: set[str] = set()
        for key, items in groups.items():
            if len(items) < 2:
                continue
            amounts = [tx.amount for tx in items]
            avg = sum(amounts, Decimal("0.00")) / Decimal(len(amounts))
            if avg <= Decimal("0.00"):
                continue
            if all(
                abs(tx.amount - avg) <= max(Decimal("5000.00"), avg * Decimal("0.25"))
                for tx in items
            ):
                recurring.add(key)
        return recurring

    def _category_trends(self, periods: list[dict[str, Any]]) -> dict[str, str]:
        categories: set[str] = set()
        for period in periods:
            for category in period.get("spending_by_category", {}):
                categories.add(category)
        if not categories:
            return {}

        trend_map: dict[str, str] = {}
        for category in sorted(categories):
            values = [
                Decimal(str(period.get("spending_by_category", {}).get(category, 0)))
                for period in periods
            ]
            trend_map[category] = self._classify_trend([int(v) for v in values])
        return trend_map

    def _detect_significant_changes(
        self,
        periods: list[dict[str, Any]],
        expense_recurring_sources: set[str] | None = None,
        income_recurring_sources: set[str] | None = None,
    ) -> tuple[list[str], list[FinancialObservation]]:
        notable: list[str] = []
        observations: list[FinancialObservation] = []

        if expense_recurring_sources:
            for k in sorted(expense_recurring_sources):
                msg = f"Recurring expense source pattern detected: {k}."
                notable.append(msg)
                observations.append(
                    FinancialObservation(
                        type="recurring_expense_pattern",
                        subject=k,
                        period=None,
                        value=None,
                        comparison=None,
                        change_amount=None,
                        change_percentage=None,
                        significant=True,
                        evidence=[msg],
                    )
                )

        if income_recurring_sources:
            for k in sorted(income_recurring_sources):
                msg = f"Recurring income source pattern detected: {k}."
                notable.append(msg)
                observations.append(
                    FinancialObservation(
                        type="recurring_income_pattern",
                        subject=k,
                        period=None,
                        value=None,
                        comparison=None,
                        change_amount=None,
                        change_percentage=None,
                        significant=True,
                        evidence=[msg],
                    )
                )

        if len(periods) < max(2, self.MINIMUM_OBSERVATION_PERIODS):
            return notable, observations

        for idx in range(1, len(periods)):
            prev = periods[idx - 1]
            curr = periods[idx]

            # Overall expenses change
            prev_exp = Decimal(str(prev.get("observed_expenses", 0)))
            curr_exp = Decimal(str(curr.get("observed_expenses", 0)))
            expense_delta = curr_exp - prev_exp
            if prev_exp != Decimal(0):
                expense_ratio = abs(expense_delta / prev_exp)
                if (
                    expense_ratio >= self.SIGNIFICANT_CHANGE_PERCENT
                    and abs(expense_delta) >= self.MINIMUM_ABSOLUTE_CHANGE
                ):
                    direction_str = "increased" if expense_delta > 0 else "decreased"
                    msg = f"Expenses {direction_str} materially from {prev['period']} to {curr['period']}."
                    notable.append(msg)
                    observations.append(
                        FinancialObservation(
                            type="expense_change",
                            subject="overall_expenses",
                            period=curr["period"],
                            value=curr_exp,
                            comparison=prev_exp,
                            change_amount=expense_delta,
                            change_percentage=(expense_ratio * Decimal(100)).quantize(
                                Decimal("0.01")
                            ),
                            significant=True,
                            evidence=[msg],
                        )
                    )

            # Overall income change
            prev_inc = Decimal(str(prev.get("observed_income", 0)))
            curr_inc = Decimal(str(curr.get("observed_income", 0)))
            income_delta = curr_inc - prev_inc
            if prev_inc != Decimal(0):
                income_ratio = abs(income_delta / prev_inc)
                if (
                    income_ratio >= self.SIGNIFICANT_CHANGE_PERCENT
                    and abs(income_delta) >= self.MINIMUM_ABSOLUTE_CHANGE
                ):
                    direction_str = "increased" if income_delta > 0 else "decreased"
                    msg = f"Income {direction_str} materially from {prev['period']} to {curr['period']}."
                    notable.append(msg)
                    observations.append(
                        FinancialObservation(
                            type="income_change",
                            subject="overall_income",
                            period=curr["period"],
                            value=curr_inc,
                            comparison=prev_inc,
                            change_amount=income_delta,
                            change_percentage=(income_ratio * Decimal(100)).quantize(
                                Decimal("0.01")
                            ),
                            significant=True,
                            evidence=[msg],
                        )
                    )

            # Category additions/removals and material changes
            prev_cats = set(prev.get("spending_by_category", {}).keys())
            curr_cats = set(curr.get("spending_by_category", {}).keys())
            all_cats = prev_cats.union(curr_cats)

            for category in sorted(all_cats):
                prev_total = Decimal(str(prev.get("spending_by_category", {}).get(category, 0)))
                curr_total = Decimal(str(curr.get("spending_by_category", {}).get(category, 0)))
                if prev_total == Decimal(0) and curr_total >= self.MINIMUM_ABSOLUTE_CHANGE:
                    msg = f"New category {category.upper()} appeared with spending {int(curr_total)} in {curr['period']}."
                    notable.append(msg)
                    observations.append(
                        FinancialObservation(
                            type="category_new",
                            subject=category,
                            period=curr["period"],
                            value=curr_total,
                            comparison=prev_total,
                            change_amount=(curr_total - prev_total),
                            change_percentage=Decimal("100.00"),
                            significant=True,
                            evidence=[msg],
                        )
                    )
                elif curr_total == Decimal(0) and prev_total >= self.MINIMUM_ABSOLUTE_CHANGE:
                    msg = f"Category {category.upper()} disappeared (was {int(prev_total)}) in {curr['period']}."
                    notable.append(msg)
                    observations.append(
                        FinancialObservation(
                            type="category_removed",
                            subject=category,
                            period=curr["period"],
                            value=curr_total,
                            comparison=prev_total,
                            change_amount=(curr_total - prev_total),
                            change_percentage=Decimal("-100.00"),
                            significant=True,
                            evidence=[msg],
                        )
                    )
                elif prev_total != Decimal(0):
                    cat_delta = curr_total - prev_total
                    cat_ratio = abs(cat_delta / prev_total)
                    if (
                        cat_ratio >= self.SIGNIFICANT_CHANGE_PERCENT
                        and abs(cat_delta) >= self.MINIMUM_ABSOLUTE_CHANGE
                    ):
                        direction_str = "increased" if cat_delta > 0 else "decreased"
                        msg = f"{category.upper()} spending {direction_str} materially from {prev['period']} to {curr['period']}."
                        notable.append(msg)
                        observations.append(
                            FinancialObservation(
                                type="category_change",
                                subject=category,
                                period=curr["period"],
                                value=curr_total,
                                comparison=prev_total,
                                change_amount=cat_delta,
                                change_percentage=(cat_ratio * Decimal(100)).quantize(
                                    Decimal("0.01")
                                ),
                                significant=True,
                                evidence=[msg],
                            )
                        )

            # Recurring additions/removals
            prev_keys = set(prev.get("recurring_expense_keys", []))
            curr_keys = set(curr.get("recurring_expense_keys", []))
            added = curr_keys - prev_keys
            removed = prev_keys - curr_keys

            for k in sorted(added):
                msg = f"Recurring expense source added: {k} in {curr['period']}."
                notable.append(msg)
                observations.append(
                    FinancialObservation(
                        type="recurring_added",
                        subject=k,
                        period=curr["period"],
                        value=None,
                        comparison=None,
                        change_amount=None,
                        change_percentage=None,
                        significant=True,
                        evidence=[msg],
                    )
                )
            for k in sorted(removed):
                msg = f"Recurring expense source removed: {k} in {curr['period']}."
                notable.append(msg)
                observations.append(
                    FinancialObservation(
                        type="recurring_removed",
                        subject=k,
                        period=curr["period"],
                        value=None,
                        comparison=None,
                        change_amount=None,
                        change_percentage=None,
                        significant=True,
                        evidence=[msg],
                    )
                )

        return notable, observations

    def _income_variability_label(self, cov: float, num_periods: int) -> str:
        if num_periods < 2:
            return "INSUFFICIENT_DATA"
        if cov <= 15.0:
            return "STABLE"
        if cov <= 30.0:
            return "MODERATE"
        return "HIGHLY_VARIABLE"

    def _category_historical_averages(self, periods: list[dict[str, Any]]) -> dict[str, int]:
        if not periods:
            return {}
        cat_sums: dict[str, Decimal] = defaultdict(Decimal)
        for period in periods:
            for cat, amount in period.get("spending_by_category", {}).items():
                cat_sums[cat] += Decimal(str(amount))
        num_periods = Decimal(len(periods))
        return {
            cat: int((total / num_periods).quantize(Decimal(1)))
            for cat, total in sorted(cat_sums.items())
        }

    def _build_period_comparisons(
        self,
        periods: list[dict[str, Any]],
        category_averages: dict[str, int],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if len(periods) < 2:
            return {}, {}

        curr = periods[-1]
        prev = periods[-2]

        curr_inc = Decimal(str(curr.get("observed_income", 0)))
        prev_inc = Decimal(str(prev.get("observed_income", 0)))
        inc_delta = curr_inc - prev_inc
        inc_pct = (
            ((inc_delta / prev_inc) * Decimal(100)).quantize(Decimal("0.01"))
            if prev_inc > 0
            else Decimal("100.00")
            if inc_delta > 0
            else Decimal("0.00")
        )

        curr_exp = Decimal(str(curr.get("observed_expenses", 0)))
        prev_exp = Decimal(str(prev.get("observed_expenses", 0)))
        exp_delta = curr_exp - prev_exp
        exp_pct = (
            ((exp_delta / prev_exp) * Decimal(100)).quantize(Decimal("0.01"))
            if prev_exp > 0
            else Decimal("100.00")
            if exp_delta > 0
            else Decimal("0.00")
        )

        cat_changes: dict[str, Any] = {}
        all_cats = set(curr.get("spending_by_category", {}).keys()).union(
            prev.get("spending_by_category", {}).keys()
        )
        for cat in sorted(all_cats):
            c_val = Decimal(str(curr.get("spending_by_category", {}).get(cat, 0)))
            p_val = Decimal(str(prev.get("spending_by_category", {}).get(cat, 0)))
            d_val = c_val - p_val
            pct = (
                ((d_val / p_val) * Decimal(100)).quantize(Decimal("0.01"))
                if p_val > 0
                else Decimal("100.00")
                if d_val > 0
                else Decimal("0.00")
            )
            cat_changes[cat] = {
                "current": int(c_val),
                "previous": int(p_val),
                "change_amount": int(d_val),
                "change_percentage": float(pct),
            }

        latest_vs_previous = {
            "period": curr["period"],
            "previous_period": prev["period"],
            "income": {
                "current": int(curr_inc),
                "previous": int(prev_inc),
                "change_amount": int(inc_delta),
                "change_percentage": float(inc_pct),
            },
            "expenses": {
                "current": int(curr_exp),
                "previous": int(prev_exp),
                "change_amount": int(exp_delta),
                "change_percentage": float(exp_pct),
            },
            "category_changes": cat_changes,
        }

        # Latest vs average
        hist_avg_inc = self._average_amount(
            [Decimal(str(p.get("observed_income", 0))) for p in periods]
        )
        hist_avg_exp = self._average_amount(
            [Decimal(str(p.get("observed_expenses", 0))) for p in periods]
        )

        inc_avg_delta = curr_inc - hist_avg_inc
        inc_avg_pct = (
            ((inc_avg_delta / hist_avg_inc) * Decimal(100)).quantize(Decimal("0.01"))
            if hist_avg_inc > 0
            else Decimal("100.00")
            if inc_avg_delta > 0
            else Decimal("0.00")
        )

        exp_avg_delta = curr_exp - hist_avg_exp
        exp_avg_pct = (
            ((exp_avg_delta / hist_avg_exp) * Decimal(100)).quantize(Decimal("0.01"))
            if hist_avg_exp > 0
            else Decimal("100.00")
            if exp_avg_delta > 0
            else Decimal("0.00")
        )

        cat_vs_avg: dict[str, Any] = {}
        for cat, avg_val_int in sorted(category_averages.items()):
            c_val = Decimal(str(curr.get("spending_by_category", {}).get(cat, 0)))
            a_val = Decimal(str(avg_val_int))
            d_val = c_val - a_val
            pct = (
                ((d_val / a_val) * Decimal(100)).quantize(Decimal("0.01"))
                if a_val > 0
                else Decimal("100.00")
                if d_val > 0
                else Decimal("0.00")
            )
            cat_vs_avg[cat] = {
                "current": int(c_val),
                "historical_average": int(a_val),
                "change_amount": int(d_val),
                "change_percentage": float(pct),
            }

        latest_vs_average = {
            "period": curr["period"],
            "income": {
                "current": int(curr_inc),
                "historical_average": int(hist_avg_inc),
                "change_amount": int(inc_avg_delta),
                "change_percentage": float(inc_avg_pct),
            },
            "expenses": {
                "current": int(curr_exp),
                "historical_average": int(hist_avg_exp),
                "change_amount": int(exp_avg_delta),
                "change_percentage": float(exp_avg_pct),
            },
            "category_vs_average": cat_vs_avg,
        }

        return latest_vs_previous, latest_vs_average

    def _build_all_financial_observations(
        self,
        periods: list[dict[str, Any]],
        category_averages: dict[str, int],
        change_observations: list[FinancialObservation],
        *,
        income_variability: float,
        income_variability_label: str,
        expense_recurring_sources: set[str] | None = None,
        income_recurring_sources: set[str] | None = None,
    ) -> list[FinancialObservation]:
        obs: list[FinancialObservation] = []

        if periods:
            curr = periods[-1]
            c_inc = Decimal(str(curr.get("observed_income", 0)))
            c_exp = Decimal(str(curr.get("observed_expenses", 0)))

            obs.append(
                FinancialObservation(
                    type="income_observed",
                    subject="overall_income",
                    period=curr["period"],
                    value=c_inc,
                    significant=False,
                    evidence=[f"Observed income in {curr['period']}: {int(c_inc)} NGN"],
                )
            )

            obs.append(
                FinancialObservation(
                    type="expense_observed",
                    subject="overall_expenses",
                    period=curr["period"],
                    value=c_exp,
                    significant=False,
                    evidence=[f"Observed expenses in {curr['period']}: {int(c_exp)} NGN"],
                )
            )

            for cat, avg_val in sorted(category_averages.items()):
                c_cat = Decimal(str(curr.get("spending_by_category", {}).get(cat, 0)))
                a_cat = Decimal(str(avg_val))
                diff = c_cat - a_cat
                pct = (
                    ((diff / a_cat) * Decimal(100)).quantize(Decimal("0.01"))
                    if a_cat > 0
                    else Decimal("100.00")
                    if diff > 0
                    else Decimal("0.00")
                )
                obs.append(
                    FinancialObservation(
                        type="category_spending",
                        subject=cat,
                        period=curr["period"],
                        value=c_cat,
                        comparison=a_cat,
                        change_amount=diff,
                        change_percentage=pct,
                        significant=abs(diff) >= self.MINIMUM_ABSOLUTE_CHANGE
                        and abs(pct) >= Decimal("20.00"),
                        evidence=[
                            f"{cat.upper()} spending in {curr['period']} is {int(c_cat)} NGN vs historical average of {avg_val} NGN ({pct}%)."
                        ],
                    )
                )

        obs.append(
            FinancialObservation(
                type="income_variability",
                subject="income_stability",
                period=None,
                value=Decimal(str(income_variability)),
                significant=income_variability_label == "HIGHLY_VARIABLE",
                evidence=[
                    f"Income variability is {income_variability}% ({income_variability_label})."
                ],
            )
        )

        if change_observations:
            obs.extend(change_observations)

        return obs

    def _build_budget_review_signals_from_observations(
        self,
        change_observations: list[FinancialObservation],
    ) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        for obs in change_observations:
            if not obs.significant:
                continue
            reason_msg = (
                obs.evidence[0]
                if obs.evidence
                else f"Significant change detected in {obs.subject}."
            )
            signal_model = BudgetReviewSignal(
                detected=True,
                reason=reason_msg,
                affected_area=obs.subject,
                observation=reason_msg,
                evidence=obs.evidence,
                change_percentage=obs.change_percentage,
                current_value=obs.value,
                historical_baseline=obs.comparison,
            )
            signals.append(signal_model.model_dump(mode="json"))
        return signals
