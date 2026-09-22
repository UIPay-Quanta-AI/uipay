# Quanta ASR Subsystem (Steps 11.1–11.6)

This document provides technical documentation for the Automatic Speech Recognition (ASR) subsystem in Quanta.

---

## 1. Target Architecture

```
                       Quanta Application / Orchestration
                                       │
                                       ▼
                                  ASRProvider (Base Interface)
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
           NaijaVoxProvider                      FasterWhisperProvider
         (Axiveri/NaijaVox-2.0)                       (large-v3)
                    │                                     │
                    ▼                                     ▼
               Transformers                         faster-whisper
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       ▼
                             Shared Audio Decoder
                                (PyAV / av)
                                       │
                                       ▼
                                   ASRResult
```

### Provider Selection
The ASR provider is resolved via `get_asr_provider()` using `Settings.ASR_PROVIDER`:
- `"naijavox"` (Primary / Default): Uses `Axiveri/NaijaVox-2.0`.
- `"faster_whisper"` (Alternative): Uses `faster-whisper` CTranslate2 backend with `large-v3`.

---

## 2. ASR Contract & Result Model

### `ASRResult`
All ASR providers return a normalized `ASRResult` instance:
- `text: str`: Non-empty transcribed text with surrounding whitespace removed.
- `language: str | None`: Canonical language code (`en`, `pcm`, `yo`, `ha`, `ig`) or `None`.
- `confidence: float | None`: Confidence score between `0.0` and `1.0` (or `None`).
- `duration_seconds: float | None`: Audio duration in seconds.
- `provider: str`: Identifier of the provider (`"naijavox"` or `"faster_whisper"`).
- `metadata: dict[str, Any]`: Provider-specific diagnostic metadata (e.g. `model_id`, `device`). Also accessible via alias `provider_metadata`.

---

## 3. Supported Languages & Normalization

The system normalizes language hints and input codes to five canonical Nigerian language codes:
- `en`: Nigerian English / English
- `pcm`: Nigerian Pidgin
- `yo`: Yoruba
- `ha`: Hausa
- `ig`: Igbo

Aliases such as `"english"`, `"Nigerian Pidgin"`, `"yoruba"`, `"hausa"`, `"igbo"`, etc. are automatically mapped to canonical codes by `normalize_language()`. Unknown language inputs raise `ASRInputError`.

---

## 4. Shared Audio Decoder (`app/providers/asr/audio.py`)

Audio bytes are decoded using **PyAV (`av`)** into a normalized representation:
- **Format:** Mono float32 PCM samples at 16,000 Hz.
- **Validation:** Enforces configurable limits (`ASR_MAX_AUDIO_BYTES`, `ASR_MAX_DURATION_SECONDS`).
- **Error Handling:** Empty inputs, corrupt data, oversized files, or audio-less media raise `ASRInputError`.

---

## 5. Primary Provider: NaijaVox-2.0 (`app/providers/asr/naijavox.py`)

- **Default Model:** `Axiveri/NaijaVox-2.0`
- **Lazy Loading:** Model and processor are loaded only on the first transcription request.
- **Tokenizer Fallback Strategy:**
  1. *Attempt 1:* Loads `WhisperProcessor.from_pretrained(MODEL_ID)` and verifies custom tokens `<|pcm|>` and `<|ig|>` in the vocabulary.
  2. *Attempt 2 (Fallback):* If custom tokens are missing, downloads `tokenizer.json` via `hf_hub_download`, constructs `PreTrainedTokenizerFast`, ensures special tokens exist, and builds `WhisperProcessor(feature_extractor, tokenizer)`.
  3. Raises `ASRModelLoadError` if both attempts fail.
- **Decoder Prompt Control:** Explicit language selection maps canonical codes (`yo`, `ha`, `ig`, `en`, `pcm`) to prompt tokens (`<|yo|>`, `<|ha|>`, `<|ig|>`, `<|en|>`, `<|pcm|>`).

---

## 6. Alternative Provider: faster-whisper (`app/providers/asr/faster_whisper.py`)

- **Default Model:** `large-v3`
- **Backend:** CTranslate2 / `faster-whisper`
- **Configurable Compute:** Supports `compute_type` (`auto`, `float16`, `int8`, `float32`).

---

## 7. Device Resolution

Device configuration (`ASR_NAIJAVOX_DEVICE`, `ASR_FASTER_WHISPER_DEVICE`):
- `device="auto"`: Uses CUDA if PyTorch reports `torch.cuda.is_available()`, otherwise CPU.
- `device="cpu"`: Forces CPU execution.
- `device="cuda"`: Requires CUDA. If CUDA is unavailable, raises `ASRConfigurationError`.

---

## 8. Configuration (`app/core/config.py`)

| Setting | Default | Description |
|---|---|---|
| `ASR_PROVIDER` | `"naijavox"` | Selected provider (`"naijavox"` or `"faster_whisper"`) |
| `ASR_MAX_AUDIO_BYTES` | `10000000` | Max audio file size limit (10 MB) |
| `ASR_MAX_DURATION_SECONDS` | `60.0` | Max audio duration limit (60s) |
| `ASR_NAIJAVOX_MODEL_ID` | `"Axiveri/NaijaVox-2.0"` | HuggingFace repository ID for NaijaVox |
| `ASR_NAIJAVOX_DEVICE` | `"auto"` | Device for NaijaVox (`auto`, `cpu`, `cuda`) |
| `ASR_FASTER_WHISPER_MODEL` | `"large-v3"` | Model name for faster-whisper |
| `ASR_FASTER_WHISPER_DEVICE` | `"auto"` | Device for faster-whisper (`auto`, `cpu`, `cuda`) |
| `ASR_FASTER_WHISPER_COMPUTE_TYPE` | `"auto"` | Compute type (`auto`, `float16`, `int8`, `float32`) |

---

## 9. Testing & Smoke Test Instructions

### Running Unit Tests (Mocked)
Unit tests mock heavyweight model loading and inference. No models are downloaded during `pytest`.
```bash
.venv\Scripts\python.exe -m pytest tests/unit/providers/asr -v
```

### Environment Check
Inspect installed packages and hardware status:
```bash
.venv\Scripts\python.exe scripts/check_asr_environment.py
```

### Real Audio Smoke Test
Run an actual audio file through the ASR engine (downloads model if not cached):
```bash
.venv\Scripts\python.exe scripts/asr_smoke_test.py path/to/audio.wav --provider naijavox --language pcm
```

---

## 10. Scope Boundaries (Out of Scope for Steps 11.1–11.6)

The following components belong to Step 11.7+ and are **intentionally not yet implemented**:
- Voice service and `/v1/voice` API endpoints
- React Native Web audio capture / frontend UI
- TTS, OCR, or Voice Auth
- Claude orchestration for voice
- Redis, database, or cloud deployment changes
