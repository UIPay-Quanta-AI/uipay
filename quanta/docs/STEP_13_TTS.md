# Quanta Text-to-Speech Subsystem (Step 13)

This document provides technical documentation for the provider-neutral Text-to-Speech (TTS) subsystem in Quanta.

---

## 1. Architecture Overview

```
                      Claude / Quanta Orchestration
                                   │
                                   ▼
                              TTSService
                                   │
                                   ▼
                             VoiceResolver
                                   │
                 ┌─────────────────┴─────────────────┐
                 ▼                                   ▼
          EdgeTTSProvider                   NaijaLingoProvider
        (Nigerian English)                 (Hausa, Igbo, Yoruba, Pidgin)
                 │                                   │
                 ▼                                   ▼
             edge-tts                            9jaLingo SDK
                 │                                   │
                 └─────────────────┬─────────────────┘
                                   ▼
                               TTSResult
                         (audio, content_type)
```

The design maintains provider neutrality across Nigerian English (`edge-tts`) and indigenous Nigerian languages (`9jaLingo`).

---

## 2. Supported Languages & Provider Routing

| Language Code | Canonical Name | Provider | Female Voice | Male Voice |
|---|---|---|---|---|
| `en` | Nigerian English | `edge` | `en-NG-EzinneNeural` | `en-NG-AbeoNeural` |
| `ha` | Hausa | `naijalingo` | `maryam_ha` | `abdullahi_ha` |
| `ig` | Igbo | `naijalingo` | `obianuju_ig` | `okechukwu_ig` |
| `yo` | Yoruba | `naijalingo` | `abisoye_yo` | `babatunde_yo` |
| `pcm` | Nigerian Pidgin | `naijalingo` | `dora_pcm` | `frank_pcm` |

Language inputs such as `"english"`, `"hausa"`, `"igbo"`, `"yoruba"`, `"pidgin"`, or locale variants like `"en-NG"` are automatically normalized by `resolve_voice()`.

---

## 3. Core Components

### 1. `TTSResult` (`app/providers/tts/base.py`)
Normalized result model:
- `audio: bytes`: Raw synthesized audio bytes.
- `content_type: str`: Content MIME type (e.g. `"audio/mpeg"` for Edge TTS, `"audio/wav"` for 9jaLingo).
- `duration_seconds: float | None`: Optional audio duration in seconds.
- `provider_metadata: dict[str, str]`: Metadata dictionary containing `provider`, `voice`, and `language`.

### 2. `VoiceResolver` (`app/providers/tts/voices.py`)
Maps high-level `(language, gender)` preferences to specific `(provider, voice_id)`. Default voice mappings are defined in `DEFAULT_VOICES` dictionary and can be easily adjusted without code refactoring or database dependencies.

### 3. Edge TTS Provider (`app/providers/tts/edge.py`)
- Provider implementation for Microsoft Edge Online TTS using `edge-tts==7.2.8`.
- Does not require Azure credentials or API keys.
- Operates asynchronously without blocking the event loop.

### 4. 9jaLingo Provider (`app/providers/tts/naijalingo.py`)
- Provider implementation for African indigenous languages using `naijalingo==2.0.6`.
- Requires `NAIJALINGO_API_KEY` configured in `.env`.
- Uses `asyncio.to_thread` to run synchronous SDK calls cleanly without blocking the event loop.
- Exposes optional provider-level streaming capability (`stream()`) yielding audio chunks asynchronously.
- Implements narrow single-retry speaker fallback if configured speaker ID is missing or returns 404.

### 5. Provider Factory (`app/providers/tts/factory.py`)
Factory function `get_tts_provider(provider_name)` resolving `"edge"` or `"naijalingo"` instances.

### 6. TTS Service (`app/services/tts.py`)
Orchestration layer combining voice resolution, provider factory lookup, and synthesis execution.

---

## 4. Configuration

Configured in `app/core/config.py` and `.env`:

```env
TTS_PROVIDER=edge
TTS_DEFAULT_GENDER=female
NAIJALINGO_API_KEY=your_naijalingo_api_key_here
```

---

## 5. Testing & Smoke Test Instructions

### Running Offline Unit Tests
Offline unit tests mock provider SDKs and require no internet or credentials:
```bash
.venv\Scripts\python.exe -m pytest tests/unit/providers/tts tests/unit/services/test_tts_service.py -v
```

### Real Synthesis Smoke Test
Runs real synthesis across Edge and 9jaLingo (if API key is present) and writes audio files to `output_audio/`:
```bash
.venv\Scripts\python.exe scripts/tts_smoke_test.py
```

### Real Streaming Smoke Test
Tests 9jaLingo streaming audio generation and reports Time-To-First-Chunk (TTFC):
```bash
.venv\Scripts\python.exe scripts/tts_stream_smoke_test.py
```

---

## 6. Security & Error Handling

- `NAIJALINGO_API_KEY` is read strictly from settings and never printed or exposed in logs.
- All SDK/third-party exceptions are caught and wrapped into provider-neutral `TTSProviderError` or `TTSConfigurationError`.
- Input text is validated to prevent empty or whitespace-only synthesis requests.
- No sensitive financial credentials or PINs are ever passed to the TTS presentation layer.
