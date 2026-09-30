# Quanta AI — Orchestration Microservice for UI Pay

Quanta is the AI-powered financial reasoning, multimodal interpretation, and governed workflow orchestration microservice for UI Pay.

## Core Invariant

> **LLM proposes. Quanta governs. UI Pay authorizes and executes.**
> Quanta interprets intent, performs deterministic budget calculations, processes multimodal inputs, and prepares transfer workflows. It **never** stores authoritative account balances, bypasses user PIN confirmation, or independently executes financial transactions.

---

## Key Features & Capabilities

1. **Governed Tool Execution**: LLM proposes tool calls, but `ToolExecutor` and `ToolPolicy` strictly enforce identity, state invariants, and argument validation.
2. **Financial Profile Lifecycle**: Manages lazy default initialization, singleton profile persistence semantics, and income/expense planning.
3. **Savings Goal Domain**: Full creation, updates, retrieval, and explicit completion tracking.
4. **Versioned Category Budgets**: Generates $v1 \rightarrow v2$ category budgets consuming `TransactionBudgetContext` (historical trends, category averages, observed income).
5. **Significant Change Detection**: Detects $\ge 25\%$ spending shifts and recommends budget adaptations requiring user acceptance.
6. **Multimodal & Voice Security**: Untrusted OCR input shielding against prompt injection; Picovoice Eagle speaker verification gating ASR; canonical language support (`en`, `pcm`, `ig`, `yo`, `ha`).
7. **Production-Ready UI Pay Adapter**: `RealUIPayClient` HTTP adapter with correlation tracing (`X-Request-ID`), safe non-retrying write policies, and structured error mapping.

---

## Project Structure

```text
quanta/
├── app/
│   ├── api/             # FastAPI endpoints (interact, voice, multimodal, health)
│   ├── clients/         # UI Pay backend HTTP adapters (base, mock, real)
│   ├── core/            # Context, config, logging, observability, exceptions
│   ├── domain/          # Financial profile, goals, budget, transaction intelligence, transfer
│   ├── orchestration/   # Orchestrator, state machine, multimodal & voice pipelines, workflow runner
│   ├── prompts/         # System prompts, safety rules, language prompts
│   ├── providers/       # LLM, ASR (NaijaVox, Whisper), Speaker (Eagle), OCR (PaddleOCR), TTS (Edge)
│   ├── schemas/         # Request, response, tool, state, and confirmation schemas
│   └── tools/           # Tool registry, policy, executor, and tool implementations
├── docs/                # Architecture, API, security, testing, integration contracts
├── tests/               # Unit, integration, contract, security, and multilingual test suite
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Quick Start & Verification

```bash
# 1. Environment Setup
.venv\Scripts\python.exe -m pytest tests/

# 2. Run Ruff Linting
.venv\Scripts\python.exe -m ruff check .

# 3. Start Quanta Server
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

---

## Integration Contracts & Handoff Docs

For integration details with the Node.js Quanta Proxy and UI Pay Backend, review:
- [`docs/uipay-client-contract.md`](file:///c:/Users/HP/Desktop/UIPay/uipay/quanta/docs/uipay-client-contract.md): Client interface, endpoints, retries, and profile singleton contract.
- [`docs/proxy-integration-contract.md`](file:///c:/Users/HP/Desktop/UIPay/uipay/quanta/docs/proxy-integration-contract.md): Node.js Proxy gateway contract, trust model, headers, and handoff guidelines.
- [`docs/architecture.md`](file:///c:/Users/HP/Desktop/UIPay/uipay/quanta/docs/ARCHITECTURE.md): Microservice architecture and ownership boundaries.
- [`docs/security.md`](file:///c:/Users/HP/Desktop/UIPay/uipay/quanta/docs/SECURITY.md): Identity boundaries, prompt injection defense, and voice authorization limits.
- [`docs/testing.md`](file:///c:/Users/HP/Desktop/UIPay/uipay/quanta/docs/testing.md): Test pyramid and safety guidelines.
- [`docs/deployment.md`](file:///c:/Users/HP/Desktop/UIPay/uipay/quanta/docs/deployment.md): Configuration settings and deployment procedures.