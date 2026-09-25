# Quanta AI — Budget Architecture, Generation, Versioning & Transaction Context

This document details the architectural design, domain semantics, security boundaries, and tool specifications for **Step 18 (Budget Generation)** and **Step 19 (Budget Updating & Versioning)** inside Quanta AI.

---

## 1. High-Level Architecture & Flow

Quanta acts as an AI orchestration layer inside UI Pay. Deterministic application logic, domain rules, security policy, and the UI Pay backend remain authoritative.

```text
                         ┌──────────────────────┐
                         │        LLM           │
                         │ Intent / Reasoning   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Budget Tool        │
                         │ generate/update      │
                         └──────────┬───────────┘
                                    │
                   ┌────────────────┼────────────────┐
                   │                │                │
                   ▼                ▼                ▼
             Financial         Goals          Transaction
              Profile                         Budget Context
                   │                │                │
                   └────────────────┼────────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │    BudgetService     │
                         │ deterministic rules  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Budget Domain Rules  │
                         │ validation/versioning│
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ UI Pay Client/Mock   │
                         └──────────────────────┘
```

Core Rule: **LLM proposes. Quanta governs. BudgetService calculates. UI Pay owns authoritative financial state.**

---

## 2. Budget Semantics & Period Boundaries

1. **Configurable Periods**: A budget is defined by explicit `start_date` and `end_date`. It is **NOT inherently calendar monthly** (e.g. September 10 to October 9 is a valid budget period).
2. **Updates Do NOT Restart Period**:
   - Updating a budget partway through its period (e.g., September 22) creates a new version (`v2`) for the **SAME original `start_date` and `end_date`** (September 10 → October 9).
   - Recalculates allocations for the remaining portion of the period (September 22 → October 9).
3. **Immutable Versioning**:
   - Version history is preserved (`v1` -> `v2` -> `v3`).
   - Previous versions remain unchanged in status `superseded`.

---

## 3. Financial Profile, Goals & Transaction Context

* **Financial Profile**: Authoritative planning input (income, fixed expenses, variable expenses, savings target).
* **Goals**: Authoritative planning input (active savings targets).
* **TransactionBudgetContext**: Optional supporting observational context derived from historical activity.
  - Contains `data_available`, `lookback_period` (bounded lookback up to 12 months when available), `historical_periods`, `trends`, and `notable_changes`.
  - **Graceful Fallback**: If `data_available = False`, budget generation and update operate seamlessly using Financial Profile and Goals without fabricating fake historical data.

---

## 4. Security & Context Boundaries

* **RequestContext**: User identity (`user_id`) is strictly extracted from trusted `RequestContext`. LLM input parameters cannot override or specify user identity.
* **Tool Policies**:
  - `generate_budget` → `ToolClassification.WRITE`
  - `update_budget` → `ToolClassification.WRITE`
  - `get_current_budget` → `ToolClassification.SENSITIVE_READ`
  - `get_budget_history` → `ToolClassification.SENSITIVE_READ`

---

## 5. Future Step 20 Integration Boundary

Step 20 will own deep transaction intelligence (categorization, anomaly detection, autonomous change detection).

The architectural boundary between Step 19 and Step 20 is:

```text
Step 20 (Transaction Intelligence)
→ Analyzes transactions, detects changes, suggests potential budget updates.

Step 19 (Budget Updating)
→ Performs authoritative budget updates after explicit user acceptance.
→ Preserves original start_date and end_date, calculates remaining period, creates new version.
```
