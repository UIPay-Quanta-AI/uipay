# UI Pay Backend Client Integration Contract

## 1. Overview & Architectural Boundaries

Quanta microservice depends on the abstract [`UIPayClient`](file:///c:/Users/HP/Desktop/UIPay/uipay/quanta/app/clients/ui_pay/base.py) interface. 
Two concrete adapters are available:
1. `MockUIPayClient`: In-memory deterministic mock for local development, unit, workflow, and E2E testing.
2. `RealUIPayClient`: Production HTTP adapter communicating with the host UI Pay backend.

### Architectural Invariant
> **LLM proposes. Quanta governs. UI Pay authorizes and owns authoritative financial state.**
> Quanta does *not* store authoritative account balances, user PINs, or transaction ledgers. All financial transactions require explicit authorization at the UI Pay boundary.

---

## 2. Authentication, Header & Correlation ID Contract

### Request Headers

All HTTP requests dispatched by `RealUIPayClient` include standard correlation headers:

| Header | Description | Example |
| :--- | :--- | :--- |
| `Content-Type` | Application payload format | `application/json` |
| `Authorization` | Service bearer token (optional) | `Bearer secret_service_token` |
| `X-Request-ID` | Request correlation ID derived from `RequestContext` | `b53298a0-7164-4e2a-89a3-5b8d21b71234` |
| `X-Correlation-ID` | Multi-hop trace correlation ID | `b53298a0-7164-4e2a-89a3-5b8d21b71234` |

---

## 3. FinancialProfile Singleton Contract

Financial profiles represent a user's single financial planning profile per user ID.

```
Quanta Domain Service
       │
       ▼
UIPayClient.get_or_initialize_financial_profile(user_id)
       │
       ├──► GET /api/v1/users/{user_id}/profile
       │      ├─ 200 OK ───────────► Return Profile
       │      └─ 404 Not Found
       │            │
       │            ▼
       └────► POST /api/v1/users/{user_id}/profile
              (Initializes default profile: NGN, 0 income/expenses)
```

- **Operation**: `get_or_initialize_financial_profile(*, user_id: str)`
- **Semantics**: Exactly one active profile per user ID.
- **Race Condition Handling**: If a concurrent initialization produces a 409 Conflict / duplicate key on `POST`, `RealUIPayClient` automatically falls back to `GET` to fetch the established profile.

---

## 4. Endpoint Specifications

### 4.1 Financial Profile

- `GET /api/v1/users/{user_id}/profile`
- `POST /api/v1/users/{user_id}/profile`
- `PATCH /api/v1/users/{user_id}/profile`

### 4.2 Goals

- `GET /api/v1/users/{user_id}/goals`
- `GET /api/v1/users/{user_id}/goals/{goal_id}`
- `POST /api/v1/users/{user_id}/goals`
- `PATCH /api/v1/users/{user_id}/goals/{goal_id}`

### 4.3 Budgets

- `GET /api/v1/users/{user_id}/budgets/current`
- `GET /api/v1/users/{user_id}/budgets`
- `POST /api/v1/users/{user_id}/budgets`

### 4.4 Transactions & Context

- `GET /api/v1/users/{user_id}/transactions?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /api/v1/users/{user_id}/transaction-context`

### 4.5 Beneficiaries

- `GET /api/v1/users/{user_id}/beneficiaries?query=name_or_number`

---

## 5. Retry and Timeout Policy

1. **Retryable Operations (`is_retryable=True`)**:
   - `GET` queries (reads) automatically retry on network timeouts or 5xx server errors up to `2` times with exponential backoff (`0.2s`, `0.4s`).
2. **Non-Retryable Financial Writes (`is_retryable=False`)**:
   - `POST`, `PATCH`, and write operations **fail fast without automatic retry** to prevent duplicate financial mutations.
3. **Timeout Configuration**:
   - Connect timeout: `5.0s`
   - Read/Write overall timeout: `10.0s` (configurable via `UIPAY_TIMEOUT_SECONDS`)

---

## 6. Error Taxonomy Mapping

| UI Pay Status Code | Quanta Exception Raised | Description |
| :--- | :--- | :--- |
| `401`, `403` | `UIPayAuthError` | Authentication or authorization error |
| `404` | `UIPayNotFoundError` | Resource not found |
| `400`, `422` | `UIPayValidationError` | Request payload validation failure |
| `5xx` | `UIPayServerError` | Upstream backend server error |
| Network / Connection | `UIPayConnectionError` | Network reachability failure |
| Timeout | `UIPayTimeoutError` | Request execution timed out |
