# Step 20 — Transaction Intelligence

## Purpose

Transaction Intelligence converts authoritative UI Pay transaction data into deterministic, normalized financial facts for Quanta. It does not replace the UI Pay backend, does not validate user identity from LLM input, and does not mutate budgets.

## Architecture

The service layer resolves:

1. **Transaction Access**: Authoritative fetch from UI Pay via `UIPayClient`. User identity is strictly derived from `RequestContext.user_id`.
2. **Bounded Lookback**: Configurable maximum lookback window (`TRANSACTION_MAX_LOOKBACK_DAYS = 365`). Default tool window is 365 days.
3. **Normalization & Data Quality**: Normalizes amounts, currencies, dates, and statuses. Distinguishes `NO_DATA`, `PROVIDER_FAILURE`, `INVALID_DATA_PRESENT`, and `INSUFFICIENT_HISTORY`.
4. **Status Filtering**: Historical actuals include only settled/completed transactions (`COMPLETED`, `SETTLED`). `PENDING`, `FAILED`, `CANCELLED`, and `REVERSED` are filtered out.
5. **Direction & Classification**: `direction` (INBOUND/OUTBOUND) is decoupled from `classification` (INCOME, EXPENSE, TRANSFER, OTHER, UNKNOWN).
   - `"DEBITED"` maps to `OUTBOUND`.
   - Signed raw amounts preserve direction before taking `abs(amount)`.
6. **Counterparty Resolution**: Distinguishes `MERCHANT`, `BENEFICIARY`, `EMPLOYER`, `SELF`, and `OTHER`.
   - `EXPENSE` defaults to `OTHER` unless merchant metadata exists.
   - Employer identification is evidence-based (explicit `source_type == "employer"` or recurring payroll evidence).
7. **Categorization**: Deterministic keywords and metadata mapping without LLM calls.
8. **Income Intelligence**: Total income, income variability (CoV metric & label), income trends, recurring income sources, historical averages.
9. **Expense Intelligence**: Total expenses, category totals, category percentages, category trends, recurring expenses.
10. **Historical Analysis & Comparisons**: Monthly calendar period aggregation (`YYYY-MM`), historical averages, `latest_vs_previous` and `latest_vs_average` comparisons.
11. **Significant Change Detection**: Configurable thresholds (`TRANSACTION_SIGNIFICANT_CHANGE_PERCENT = 0.20`, `TRANSACTION_MINIMUM_ABSOLUTE_CHANGE = 10000.00`, `TRANSACTION_MINIMUM_OBSERVATION_PERIODS = 2`).
12. **Structured Observations**: Generates typed `FinancialObservation` objects.
13. **Budget Review Signals**: Generates typed `BudgetReviewSignal` objects for budget review workflows without mutating budgets.
14. **TransactionBudgetContext**: Constructs full budget context for consumption by Steps 18/19.
15. **Sanitized LLM Tool Output**: `GetTransactionInsightsTool` (`SENSITIVE_READ`) exposes sanitized insights without operational IDs (`id`, `reference`) or raw provider payloads.

## Key Invariants

- `direction != classification`
- `merchant != beneficiary`
- `counterparty_type` is a relationship label, not a separate database entity hierarchy.
- `reference` and `id` are operational identifiers, excluded from LLM context.
- `SELF`, `EMPLOYER`, and `OTHER` do not require dedicated domain entity models.
- LLM output is explanatory only; financial arithmetic remains deterministic in code.
- Provider failures raise `TransactionIntelligenceServiceError` and are NOT collapsed into `data_available = False`.
- Tool execution catches exceptions silently, logs details, and returns safe public error messages.

## Security & Isolation

- **User Isolation**: Identity is strictly derived from `RequestContext.user_id`. `user_id` cannot be passed via tool input or service arguments.
- **Prompt Injection Defense**: Transaction descriptions containing malicious commands (e.g., `"IGNORE PREVIOUS INSTRUCTIONS..."`) are treated strictly as uninterpreted string data.
- **Data Minimization**: Raw payloads and operational IDs are excluded from LLM context.

## Test Pyramid & Verification

- **558 Unit & Integration Tests Passed** (0 failures, 0 lint errors).
- **Unit Tests**: Calculations, trend classifications, direction/classification separation, counterparty resolution, recurring source detection, bounded lookback, provider failure semantics.
- **Security Tests**: User isolation, prompt injection safety, lookback clamping.
- **Integration/E2E Tests**: End-to-end flow from `RequestContext` through `MockUIPayClient` to `TransactionBudgetContext` with complete numerical assertions.

