# Quanta Mega Step 1: Agent API, Conversational Workflow Layer & State Machine

## 1. Architecture Overview

Quanta Mega Step 1 completes the transition of Quanta from a basic LLM tool-calling service into a **controlled conversational financial agent microservice** for UI Pay.

```
                     ┌──────────────────────────────────────────────┐
                     │          FastAPI Endpoints Layer             │
                     │          (app/api/v1/endpoints/*)           │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │     ConversationalWorkflowRunner             │
                     │     (app/orchestration/workflow_runner.py)   │
                     └───────┬──────────────────────────────┬───────┘
                             │                              │
                             ▼                              ▼
              ┌──────────────────────────────┐   ┌───────────────────────────┐
              │    SessionState Manager      │   │  Dynamic Prompt Builder   │
              │  (app/domain/conversational) │   │ (app/prompts/builder.py)  │
              └──────────────────────────────┘   └──────────────┬────────────┘
                                                            │
                                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │           MultimodalProcessor                │
                     │       (app/orchestration/multimodal.py)      │
                     └───────┬──────────────────────────────┬───────┘
                             │                              │
                             ▼                              ▼
              ┌──────────────────────────────┐   ┌───────────────────────────┐
              │    Voice Pipeline (ASR/Eagle)│   │    OCR Provider (Paddle)  │
              └──────────────────────────────┘   └───────────────────────────┘
                                             │
                                             ▼
                     ┌──────────────────────────────────────────────┐
                     │             Orchestrator                     │
                     │      (app/orchestration/orchestrator.py)     │
                     └───────┬──────────────────────────────┬───────┘
                             │                              │
                             ▼                              ▼
              ┌──────────────────────────────┐   ┌───────────────────────────┐
              │         StateMachine         │   │   ToolRegistry / Executor │
              └──────────────────────────────┘   └──────────────┬────────────┘
                                                                │
                                                                ▼
                                                 ┌───────────────────────────┐
                                                 │     UIPayClient (HTTP)    │
                                                 └───────────────────────────┘
```

---

## 2. API Reference Specification

Quanta exposes a production-grade FastAPI v1 REST API (`/api/v1`) with 13 endpoints:

| Domain | Method | Endpoint Path | Description | Request / Form | Primary Response |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Interact** | `POST` | `/api/v1/interact` | Text interaction endpoint | `QuantaRequest` | `QuantaResponse` |
| **Interact** | `POST` | `/api/v1/interact/multipart` | Multimodal (Text + Audio + Image) | Form & File parts | `QuantaResponse` |
| **Voice** | `POST` | `/api/v1/voice/interact` | Voice interaction & transcription | Audio & Profile files | `VoicePipelineResult` |
| **Voice** | `POST` | `/api/v1/voice/enroll` | Voice speaker profile enrollment | Audio file | `VoiceEnrollmentResponse` |
| **Profile** | `GET` | `/api/v1/profile` | Retrieve user financial profile | Header `X-User-ID` | `FinancialProfile` |
| **Profile** | `POST` | `/api/v1/profile` | Create/update financial profile | `FinancialProfile` | `FinancialProfile` |
| **Budget** | `GET` | `/api/v1/budget/current` | Get current active budget | Header `X-User-ID` | `Budget` \| `None` |
| **Budget** | `POST` | `/api/v1/budget/generate` | Generate budget plan | `GenerateBudgetRequest` | `Budget` |
| **Budget** | `GET` | `/api/v1/budget/history` | Get historical budget plans | Header `X-User-ID` | `list[Budget]` |
| **Goals** | `GET` | `/api/v1/goals` | List financial goals | Query `status_filter` | `list[FinancialGoal]` |
| **Goals** | `POST` | `/api/v1/goals` | Create financial goal | `CreateGoalRequest` | `FinancialGoal` |
| **Goals** | `PUT` | `/api/v1/goals/{goal_id}` | Update financial goal | `UpdateGoalRequest` | `FinancialGoal` |
| **Tx Intel**| `GET` | `/api/v1/transactions/intelligence` | Transaction intelligence analysis | Query `start_date`, `end_date` | `TransactionIntelligenceResult` |

### Required API Headers & RequestContext Extraction
All endpoints extract trusted metadata via FastAPI `Header` dependencies into a unified `RequestContext`:
- `X-User-ID`: System authenticated user ID (never accepted from user text or LLM output).
- `X-Session-ID`: Conversation session identifier.
- `X-Locale`: Language code (`en`, `pcm`, `ig`, `yo`, `ha`).
- `X-Operation`: Operational mode (`TEXT`, `VOICE`, `MULTIMODAL`).

---

## 3. Session & State Machine Management

### Session State (`app/domain/conversational/session.py`)
Multi-turn interaction context is managed via standard `SessionState` objects containing:
- `user_id`: Authenticated user.
- `session_id`: Unique session string.
- `active_workflow`: Current active task flow (`TRANSFER`, `FINANCIAL_PROFILE_SETUP`, `BUDGET_GENERATION`, `GOAL_CREATION`, or `None`).
- `collected_data`: Partial parameter dictionary accumulated across dialogue turns.
- `messages`: Conversation history.
- `last_updated_at`: State freshness timestamp.

### State Transitions
```
                ┌───────────┐
                │   IDLE    │
                └─────┬─────┘
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
┌────────────────────┐ ┌────────────────────┐
│ TRANSFER_PROPOSED  │ │ PROFILE_QUESTIONING│
└──────────┬─────────┘ └──────────┬─────────┘
           │                      │
           ▼                      ▼
┌────────────────────┐ ┌────────────────────┐
│CONFIRMATION_REQUIRED││   SETUP_COMPLETE   │
└────────────────────┘ └────────────────────┘
```

When an interaction produces a `CONFIRMATION_REQUIRED` response (e.g. for financial transfers), the workflow state transitions to `TRANSFER_PROPOSED` and records the pending transfer parameters in `collected_data`.

---

## 4. Conversational Domain & Question Requirements

Missing planning information is identified using `FinancialProfileRequirementManager` (`app/domain/conversational/requirements.py`).

### Standardized Profile Questions (`PROFILE_QUESTIONS`)
- `monthly_income`: Monetary capacity definition.
- `income_frequency`: Cash flow schedule (`monthly`, `biweekly`, `weekly`, `irregular`).
- `employment_type`: Income stability assessment (`salaried`, `self_employed`, `freelance`, `unemployed`, `other`).
- `fixed_expenses`: Essential recurring obligations (rent, utilities).
- `variable_expenses`: Flexible spending capacity (food, transport).
- `savings_target`: Target allocation for savings goals.

---

## 5. Dynamic System Prompt Builder

The system prompt is dynamically assembled per request by `build_quanta_system_prompt` (`app/prompts/builder.py`).

### Prompt Modules (`app/prompts/*`)
1. **Core Safety & Security Invariants** (`core_safety.py`): Immutable system guardrails.
2. **Transfer Workflow Rules** (`transfer_prompts.py`): Multi-turn transfer extraction & confirmation logic.
3. **Financial Profile Setup** (`financial_profile_prompts.py`): Questioning sequence & profile completion rules.
4. **Budget Generation** (`budget_prompts.py`): 50/30/20 & zero-based budgeting rules.
5. **Goal Creation & Tracking** (`goals_prompts.py`): Target setting & contribution calculations.
6. **Transaction Intelligence** (`transaction_intelligence_prompts.py`): Categorization, trend analysis, anomaly detection.
7. **Multilingual & Nigerian English Guidance** (`multilingual.py`): Cultural context, Pidgin (`pcm`), Igbo (`ig`), Yoruba (`yo`), Hausa (`ha`).

---

## 6. Security Invariants & Guardrails

Quanta strictly enforces 10 non-negotiable security invariants across all execution paths:

1. **User Identity Binding**: `user_id` is sourced strictly from `RequestContext.user_id`.
2. **Explicit Transfer Confirmation**: No fund transfer is ever executed without explicit confirmation from the user (`QuantaState.CONFIRMATION_REQUIRED`).
3. **PIN Authentication**: Transfers above authorization limits require PIN validation.
4. **Speaker Verification**: Voice operations verify the user's voice print against enrolled embeddings.
5. **No Hallucinated Account Numbers**: Account numbers and recipient names must be validated through official bank resolution services before transfer proposal.
6. **Data Privacy**: No unmasked raw secrets or authentication credentials in logs.
7. **Idempotency**: All transactional mutations include unique request IDs.
8. **Input Sanitization**: User prompt injections and system override attempts are stripped and ignored.
9. **Strict Schema Constraints**: All tool parameters adhere to rigid Pydantic validation schemas.
10. **Graceful Failures**: System errors produce localized error responses (`QuantaResponse.error_response`) without exposing internal tracebacks to clients.

---

## 7. Multilingual & Localization Architecture

Quanta supports 5 canonical language codes across voice ASR, text prompt generation, and TTS audio synthesis:

- **`en`**: Standard English
- **`pcm`**: Nigerian Pidgin ("Abeg confirm this transfer of N50,000 to...")
- **`ig`**: Igbo ("Biko nyochaa ma kwado nnyefe a...")
- **`yo`**: Yoruba ("Jọ̀ọ́ yẹ̀ ẹ́ wò kọ́ o si fọwọ́ sí gbigbe owó yìí...")
- **`ha`**: Hausa ("Taimaka ka duba kuma ka tabbatar da tura kudin...")

---

## 8. Verification & Test Suite

The microservice includes a comprehensive automated test suite consisting of **614 passing tests** (and 2 intentionally skipped integration tests):

- **Unit Tests**: Domain models, prompt builders, tool registry, state machine, providers.
- **Integration Tests**: FastAPI endpoint tests, voice pipeline end-to-end flows, multi-turn conversational scenarios.
- **Mega Scenarios**: 12 end-to-end realistic financial scenarios (transfers, profile completion, voice enrollment, transaction intelligence).
