# Quanta Step 21: Multimodal Interaction & Language Governance

## Overview

This document details Quanta's multimodal interaction architecture and language governance model (Step 21).

Quanta supports four primary interaction modes:
1. **Flow A — Text-Only**
2. **Flow B — Voice-Only**
3. **Flow C — Image-Only**
4. **Flow D — Multimodal** (Image+Text, Image+Voice, Voice+Text, Image+Voice+Text)

Core Security Invariant:
```
LLM proposes.
Quanta governs.
UI Pay authorizes and executes.
```
Quanta **NEVER** executes a financial transfer directly. No `execute_transfer` tool exists.

---

## 1. Supported Languages & Canonical Codes

Quanta standardizes supported interaction language identifiers to five canonical codes matching NaijaVox / 9jaLingo models:

| Code | Language Name | ASR Special Token | Default TTS Voice Provider |
|---|---|---|---|
| `en` | Nigerian English | `<|en|>` | Edge TTS (`en-NG-EzinneNeural`) |
| `pcm` | Nigerian Pidgin | `<|pcm|>` | 9jaLingo (`dora_pcm`) |
| `ig` | Igbo | `<|ig|>` | 9jaLingo (`obianuju_ig`) |
| `yo` | Yoruba | `<|yo|>` | 9jaLingo (`abisoye_yo`) |
| `ha` | Hausa | `<|ha|>` | 9jaLingo (`maryam_ha`) |

**Default Language:** `en`

Regional suffixes (`en-NG`, `ig-NG`, `yo-NG`, `ha-NG`, `pcm-NG`) are mapped to canonical codes upon entry and are **NOT** passed to model tokens.

---

## 2. RequestContext.locale Semantics

> **Rule:** `RequestContext.locale` is shared interaction context, not a universal provider argument.

`RequestContext.locale` represents the user's configured/requested interaction language and shared language context. It defaults to `"en"`.

### Modality Consumption Rules

- **Voice / ASR:** `RequestContext.locale` is passed to the ASR provider as the language hint (`NaijaVox` receives language code -> resolves token `<|en|>`, `<|pcm|>`, `<|ig|>`, `<|yo|>`, `<|ha|>`).
- **Text:** No language hint is required to parse text. `RequestContext.locale` is supplied to the LLM as contextual preference, but the LLM determines the actual language of the message.
- **OCR / Image:** `RequestContext.locale` is **NOT** passed into PaddleOCR 3.7 (PP-OCRv6_medium does not support Igbo/Yoruba/Hausa parameters). Provider capability metadata dictates provider invocation.
- **Multimodal:** `RequestContext.locale` acts as shared context across all active modalities.

---

## 3. TTS Language Resolution

> **Rule:** DO NOT make TTS directly select its voice from `RequestContext.locale`.

The response language originates from the LLM orchestration result (`response_language`), decoupled from the input `RequestContext.locale`.

Flow:
```
User Input
    ↓
ASR / Text / OCR Normalization
    ↓
LLM Interpretation
    ↓
LLM Response + response_language
    ↓
TTS Service (resolve_voice)
    ↓
Provider Voice (Edge / 9jaLingo)
```

Example:
If `RequestContext.locale = "ig"` but the LLM responds in English (`response_language = "en"`), English TTS voice is selected.

---

## 4. Four Supported Input Flows

### Flow A — Text-Only
- User provides text prompt.
- LLM identifies intent and missing fields.
- Transfers prepared via deterministic `TransferContext` & `TransferGuard`.

### Flow B — Voice-Only
- User audio verified via `SpeakerProvider` (Eagle profile).
- Speech transcribed via `NaijaVoxProvider` with language hint.
- LLM processes transcript, returns `response_language`.
- Speech audio generated via `TTSService`.

### Flow C — Image-Only
- Document / screenshot text extracted via `PaddleOCRProvider`.
- Extracted text treated as **untrusted data**.
- Candidate account details validated via UI Pay backend (`AccountValidator`). Authoritative account name returned by UI Pay wins.
- Quanta prompts for missing amount.

### Flow D — Multimodal
- Combines Image + Voice, Image + Text, Voice + Text, or Image + Voice + Text.
- `MultimodalProcessor` coordinates modality extraction into a single normalized context.
- Conflicting modalities (e.g. image account vs text account) resolved using latest explicit user instruction or clarification prompt.

---

## 5. Security & Boundary Rules

1. **User Identity Isolation:** `RequestContext.user_id` is the ONLY trusted identity. `user_id` in LLM arguments, OCR text, or voice transcripts is ignored.
2. **Untrusted OCR Boundary:** Extracted OCR text is wrapped as untrusted data. Prompt injection instructions inside images or audio cannot bypass confirmation or execution boundaries.
3. **No Financial Execution:** Quanta only creates transfer preparations (`prepare_transfer`) and confirmation payloads (`QuantaResponse.confirmation_required`). UI Pay executes transfers after user PIN authorization.

---

## 6. E2E Testing Strategy

The test pyramid consists of:
- Unit tests (`tests/unit/test_step21_multimodal_and_languages.py`)
- Orchestrator and Tool tests (`tests/unit/orchestration/`, `tests/unit/tools/`)
- Four Flows Integration tests (`tests/integration/test_step21_four_flows.py`)
- Multimodal & Security Integration tests (`tests/integration/test_step21_multimodal_scenarios.py`)
