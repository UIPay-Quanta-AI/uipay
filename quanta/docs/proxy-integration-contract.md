# Node.js Quanta Proxy Integration Contract & Handoff Guidelines

> **SCOPE BOUNDARY**: The Node.js Quanta Proxy is an external gateway component developed outside the Quanta microservice repository. This document defines the Quanta-side integration contract expected by Quanta when the Proxy routes user traffic.

---

## 1. Network & Trust Architecture

```
React Native Web / PWA
        │
        ▼
UI Pay Backend (Authentication & Authoritative Ledger)
        │
        ▼
Quanta Proxy (Node.js Gateway — OUTSIDE QUANTA REPO)
        │
        ▼  HTTP (JSON / Form Data)
Quanta Microservice (Python FastAPI)
        │
        ├── /api/v1/interact
        ├── /api/v1/voice/interact
        ├── /api/v1/multimodal/interact
        └── /health
```

### Trust Boundary Rules
1. **Proxy establishes authenticated identity**: The Proxy verifies UI Pay session tokens / JWTs and injects trusted identity headers.
2. **Quanta trusts header identity**: Quanta constructs [`RequestContext`](file:///c:/Users/HP/Desktop/UIPay/uipay/quanta/app/core/context.py) from headers (`X-User-ID`, `X-Session-ID`, `X-Request-ID`).
3. **LLM arguments cannot override identity**: Quanta's `ToolExecutor` ignores any `user_id` inside LLM tool parameters and enforces the header-derived identity.

---

## 2. Header Specification

The Proxy MUST supply the following HTTP headers on every request to Quanta:

| Header Name | Type | Description | Required | Example |
| :--- | :--- | :--- | :--- | :--- |
| `X-User-ID` | String | Authenticated UI Pay user identifier | **YES** | `usr_98241a7b` |
| `X-Session-ID` | String | Unique frontend session identifier | **YES** | `sess_4812a` |
| `X-Request-ID` | String | Correlation ID for request tracing | **YES** | `req_b53298a0` |
| `Accept-Language` | String | Language preference token (`en`, `pcm`, `ig`, `yo`, `ha`) | Optional (Default: `en`) | `yo` |

---

## 3. Quanta API Endpoints

### 3.1 Conversational Text Interaction
- **Route**: `POST /api/v1/interact`
- **Content-Type**: `application/json`
- **Request Payload**:
```json
{
  "text": "Send 25,000 NGN to GTBank account 0123456789 for Mum",
  "locale": "en"
}
```
- **Response Payload**:
```json
{
  "request_id": "req_b53298a0",
  "status": "confirmation_required",
  "speech_text": "Please confirm: transfer ₦25,000 to Mum (GTBank 0123456789).",
  "display_text": "Confirm transfer of ₦25,000 to Mum",
  "ui": {
    "type": "transfer_confirmation",
    "title": "Transfer Confirmation"
  },
  "data": {
    "amount": 25000,
    "currency": "NGN",
    "beneficiary_id": "0123456789"
  }
}
```

### 3.2 Voice Pipeline Interaction
- **Route**: `POST /api/v1/voice/interact`
- **Content-Type**: `multipart/form-data`
- **Form Fields**: `audio_file` (WAV/PCM byte payload), `locale` (optional, default `en`), `speaker_profile_id` (optional).

### 3.3 Multimodal Image Interaction
- **Route**: `POST /api/v1/multimodal/interact`
- **Content-Type**: `multipart/form-data`
- **Form Fields**: `image_file` (JPEG/PNG document/screenshot), `text` (optional caption).

---

## 4. Teammate Integration Checklist for Node.js Proxy

When implementing the Node.js Proxy:

- [ ] Validate UI Pay authentication before forwarding requests to Quanta.
- [ ] Pass trusted `X-User-ID`, `X-Session-ID`, and `X-Request-ID` headers.
- [ ] Map client language selection to canonical codes: `en`, `pcm`, `ig`, `yo`, `ha` (convert `en-NG` to `en`).
- [ ] Relay structured response statuses (`success`, `confirmation_required`, `input_required`, `error`) to the frontend.
- [ ] Do not mutate Quanta response `ui.type` payloads (`TRANSFER_CONFIRMATION`, `BUDGET_SUMMARY`, `GOAL_PROGRESS`).
