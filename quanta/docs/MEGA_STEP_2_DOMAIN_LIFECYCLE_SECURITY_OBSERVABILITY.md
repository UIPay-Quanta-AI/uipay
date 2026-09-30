# Quanta Microservice — Mega Step 2 Implementation & Architecture Documentation

## 1. Overview & Non-Negotiable Invariants

Mega Step 2 hardens the Quanta microservice into a production-credible, governed financial agent. It establishes deterministic domain lifecycles across financial profiles, savings goals, category budgets, transaction intelligence, and transfer safety.

### Core Architectural Principles
- **LLM Proposes. Quanta Governs. UI Pay Authorizes and Executes.**
- **Trusted Request Context**: User identity (`user_id`) is strictly derived from trusted HTTP request headers (`RequestContext`), never from LLM arguments or prompt inputs.
- **PIN & Authorization Boundary**: Voice verification or high-confidence intent detection does *not* authorize financial transactions. Explicit user review and PIN verification at the UI Pay boundary remain mandatory.

---

## 2. Complete Domain Lifecycles & Relationships

```
                 ┌────────────────────────────────────────────────────────┐
                 │                 UI Pay Backend (Host)                  │
                 │   Authoritative Accounts, Balances, Transfers, PIN     │
                 └───────────────────────────┬────────────────────────────┘
                                             │ (UIPayClient)
                                             ▼
                 ┌────────────────────────────────────────────────────────┐
                 │                 Quanta Microservice                    │
                 └───────────────────────────┬────────────────────────────┘
                                             │
      ┌──────────────────────┬───────────────┴──────────────┬──────────────────────┐
      ▼                      ▼                              ▼                      ▼
┌───────────┐      ┌────────────────────┐         ┌────────────────────┐    ┌────────────┐
│ Financial │      │    Transaction     │         │       Goal         │    │  Transfer  │
│  Profile  │      │    Intelligence    │         │      Domain        │    │  Workflow  │
└─────┬─────┘      └─────────┬──────────┘         └─────────┬──────────┘    └─────┬──────┘
      │                      │                              │                     │
      │ (Income & Expenses)  │ (Historical Context & Trends)│ (Target Allocation) │
      └──────────────────────┼──────────────────────────────┘                     │
                             ▼                                                    │
                   ┌───────────────────┐                                          │
                   │   BudgetService   │                                          │
                   │  Versioned (v1->v2)│                                          │
                   └───────────────────┘                                          │
                                                                                  ▼
                                                                       ┌────────────────────┐
                                                                       │Explicit User Review│
                                                                       │    & Confirmation  │
                                                                       └────────────────────┘
```

### 2.1 Financial Profile Lifecycle
- **Lazy Defaults**: Default profile fields (`monthly_income = 0.00`, `fixed_expenses = 0.00`) are initialized lazily upon first query.
- **Unified Convergence**: Batch UI form entries and multi-turn conversational answers pass through identical domain schema validation (`FinancialProfileService`).

### 2.2 Goal Lifecycle
- **Explicit Completion**: `GoalService.complete_goal()` and `CompleteGoalTool` require explicit user completion commands (e.g. *"Mark my laptop goal complete"*). Budgets allocate funds to active goals without mutating goal status.

### 2.3 Budget Generation & Versioning
- **Transaction Context Integration**: `BudgetService` consumes `TransactionBudgetContext` (observed income, spending by category, recurring items).
- **Version Tracking**: Generating or updating an active budget creates a new version ($v1 \rightarrow v2$), marking previous active versions as `SUPERSEDED`.
- **Deterministic Math**: Calculations use `Decimal` precision; arithmetic is isolated from LLM prompt text.

### 2.4 Significant Change Detection & Adaptation
- **Threshold Policy**: `TransactionIntelligenceService` evaluates percentage changes ($\ge 25\%$), absolute threshold changes ($\ge ₦50,000$), and observation periods ($\ge 2$).
- **User Governance**: Significant spending shifts trigger budget adaptation *suggestions*. Mutation occurs only after explicit user acceptance.

---

## 3. Security, Voice, and Multimodal Governance

1. **Identity Hardening**:
   - `ToolExecutor` strips any `user_id` argument supplied by the LLM and injects trusted context identity (`RequestContext.user_id`).
   - Cross-user entity ownership mismatch raises domain errors (`GoalDomainError`, `ProfileDomainError`).

2. **Multimodal & Prompt Injection Defense**:
   - Extracted OCR text is treated strictly as untrusted user data.
   - System prompts shield tool execution from adversarial prompts embedded in images.

3. **Voice Authorization Invariant**:
   - Speaker verification score thresholding gates ASR.
   - Successful speaker verification confirms identity but *never* bypasses financial PIN entry.

4. **Canonical Language Tokens**:
   - Supported languages are strictly normalized to canonical 2-letter/3-letter ISO tokens: `en`, `pcm`, `ig`, `yo`, `ha`.
   - `en-NG` is mapped to canonical `en`.

---

## 4. Structured Observability & Redaction

Implemented in `app/core/observability.py`:
- **Correlation ID**: `request_id` (UUID) propagates across API endpoints, orchestrator, tools, and clients.
- **Redaction Engine**: Automatically redacts sensitive fields (`pin`, `password`, `token`, `api_key`, `bvn`, `audio`, `voice_profile`, `profile_bytes`).
- **Telemetry**: `log_request_event()`, `log_tool_execution()` (tracks tool name, latency, error status), and `log_security_decision()` (records policy checks).
- **Error Taxonomy**: Categorizes failures (`VALIDATION_ERROR`, `AUTHENTICATION_ERROR`, `AUTHORIZATION_ERROR`, `WORKFLOW_ERROR`, `PROVIDER_ERROR`, `TIMEOUT_ERROR`, `DOMAIN_ERROR`).

---

## 5. Test Verification Summary

- **Unit & Integration Suite**: 631 passed, 2 skipped (live API network tests).
- **Linter**: `ruff check .` passed with 0 errors.
