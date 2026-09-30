# Quanta Microservice — Comprehensive Testing Strategy

## 1. Test Pyramid Architecture

The Quanta test suite follows a strict multi-layered testing pyramid to guarantee deterministic financial calculations, security enforcement, and conversational accuracy.

```
                  ┌──────────────────────┐
                  │    E2E Journeys      │  (6 End-to-End Scenarios)
                  └──────────┬───────────┘
                             │
                  ┌──────────┴───────────┐
                  │   Contract Tests     │  (RealUIPayClient Transport)
                  └──────────┬───────────┘
                             │
                  ┌──────────┴───────────┐
                  │  Integration Tests   │  (Workflow Runner & Session)
                  └──────────┬───────────┘
                             │
                  ┌──────────┴───────────┐
                  │      Unit Tests      │  (Domain, Tools, Security, Prompts)
                  └──────────────────────┘
```

---

## 2. Test Execution Commands

Run tests using the project virtual environment Python binary:

```bash
# Full test suite execution
.venv\Scripts\python.exe -m pytest tests/ -v

# Specific test sub-suites
.venv\Scripts\python.exe -m pytest tests/unit/
.venv\Scripts\python.exe -m pytest tests/integration/
.venv\Scripts\python.exe -m pytest tests/contract/
.venv\Scripts\python.exe -m pytest tests/unit/security/

# Ruff linting
.venv\Scripts\python.exe -m ruff check .
```

---

## 3. Test Categories Summary

- **Unit Tests (`tests/unit/`)**: Domain calculators (budget, goals, profiles, transactions), tool executor schema validation, policy checks, prompt construction, and response synthesis.
- **Integration Tests (`tests/integration/`)**: Multi-turn session state machine, workflow runner interactions, and multimodal extraction.
- **Contract Tests (`tests/contract/`)**: `RealUIPayClient` HTTP transport using `httpx.MockTransport`, correlation ID propagation, error taxonomy status mapping, non-retrying write policies, and singleton profile initialization.
- **Security Tests (`tests/unit/security/`)**: Identity spoofing prevention, prompt injection shielding in OCR text, unauthorized tool execution blocking, and voice authorization boundary verification.
- **Multilingual Tests (`tests/unit/test_multilingual_regression.py`)**: Canonical language token verification across `en`, `pcm`, `ig`, `yo`, `ha`.

---

## 4. Safety Invariant for Automated Testing

> **NO REAL MONEY IN AUTOMATED TESTS.**
> All transfer tools and financial clients use mock transports or sandbox adapters in automated test runs. Real financial execution is strictly reserved for user PIN entry at the host UI Pay backend.
