# Step 12 — OCR Subsystem Engineering Documentation

## 1. Executive Summary & Purpose

The **OCR (Optical Character Recognition) Subsystem** provides provider-neutral, local text extraction capabilities for the Quanta AI microservice. Its primary operational role is extracting account numbers, bank names, recipient names, transaction references, and amount figures from user-uploaded images (such as bank receipts, transfer debit notes, or account detail screenshots).

Architecturally, the OCR subsystem mirrors the **ASR (Speech-to-Text)** subsystem (Step 11), adhering to the exact same design principles:
- **Provider-Neutral Interface**: A strict abstract base class contract (`OCRProvider`).
- **Local Inference Only**: No cloud API keys, tokens, or external vendor lock-in.
- **Lazy Model Loading**: Zero model downloads or initialization overhead during app startup or module imports.
- **Thread-Offloaded Execution**: Heavy blocking inference is executed in worker threads via `asyncio.to_thread()` to keep the FastAPI event loop unblocked.
- **Strict Financial-Text Preservation**: Raw OCR text is preserved without artificial post-processing or digit substitution.

---

## 2. Architecture & Subsystem Layout

The subsystem files reside within `app/providers/ocr/`:

```
app/providers/ocr/
├── __init__.py           # Unified exports for contract, providers, factory, errors
├── base.py               # Abstract contract, data models (OCRResult, OCRTextBlock), error hierarchy
├── factory.py            # Provider factory (get_ocr_provider)
├── image.py              # Image decoding, validation, and safety checks (validate_image)
└── paddleocr.py          # PaddleOCR 3.x local inference provider (PaddleOCRProvider)
```

Additional diagnostic tools and tests:
- `scripts/check_ocr_environment.py`: Environment inspector (checks dependencies and device settings without downloading models).
- `scripts/ocr_smoke_test.py`: Standalone CLI tool to run OCR on real image files.
- `tests/unit/providers/ocr/`: Comprehensive mock-based unit tests.

---

## 3. Subsystem Contract Hardening (`base.py`)

### 3.1 Data Models

#### `OCRTextBlock`
Represents a single recognized segment or line of text:
- `text` (`str`, `min_length=1`): Raw recognized text string.
- `confidence` (`float | None`, `0.0 <= confidence <= 1.0`): Model confidence score.
- `bbox` (`list[list[float]] | None`): 4-corner bounding box polygon coordinates `[[x0, y0], [x1, y1], [x2, y2], [x3, y3]]`.

#### `OCRResult`
Represents the complete OCR output for an image:
- `text` (`str`, `min_length=1`): Full reconstructed text (line-joined with newline characters).
- `blocks` (`list[OCRTextBlock]`): List of individual text block segments.
- `provider` (`str`, default `"unknown"`): Identifier of the provider used (e.g., `"paddleocr"`).
- `provider_metadata` (`dict[str, Any]`): Provider-specific execution metadata (device, timing, image dimensions).

### 3.2 Error Hierarchy

All OCR errors inherit from `OCRError`:

```
OCRError (Exception)
├── OCRConfigurationError   # Invalid settings or missing hardware requirement
├── OCRInputError           # Empty, corrupt, oversized, or unsupported image
└── OCRProviderError        # Runtime provider failures
    ├── OCRModelLoadError   # Model pipeline initialization or download failure
    └── OCRExtractionError  # Inference failure or empty text result
```

For backwards compatibility, `OCRProviderError` remains importable as a subclass of `OCRError`.

---

## 4. Image Validation & Safety (`image.py`)

Before passing byte payloads to heavy C++/Python ML runtimes, `validate_image()` inspects the raw binary data using Pillow (`PIL`):

1. **Empty Input Check**: Rejects 0-byte inputs immediately.
2. **Byte Size Limit**: Enforces `OCR_MAX_IMAGE_BYTES` (default: 20 MB).
3. **Format Verification**: Restricts formats to **PNG**, **JPEG** (including MPO alias), and **WEBP**.
4. **Resolution Cap**: Enforces `OCR_MAX_IMAGE_PIXELS` (default: 50,000,000 pixels) to protect against decompression bomb attacks.
5. **Mode Normalization**: Inspects image mode (RGB, RGBA, L) without mutating original image bytes.

Returns a `ValidatedImage` dataclass containing image metadata and the untouched original bytes.

---

## 5. PaddleOCR Provider (`paddleocr.py`)

### 5.1 Design & Execution Flow

`PaddleOCRProvider` implements local OCR using PaddleOCR 3.x:

1. **Lazy Initialization**: The `PaddleOCR` pipeline is `None` upon instantiation. On the first call to `extract()`, an `asyncio.Lock` ensures single-threaded initialization.
2. **Device Resolution**: `resolve_paddle_device()` evaluates `OCR_PADDLE_DEVICE`:
   - `"auto"`: Queries `paddle.is_compiled_with_cuda()` and CUDA device availability. Falls back to CPU if unavailable.
   - `"cpu"`: Forces CPU inference.
   - `"gpu"`: Requires CUDA GPU; raises `OCRConfigurationError` if CUDA is missing.
3. **In-Memory Inference Path**: Attempts to convert validated image bytes directly into a NumPy RGB array in-memory for `predict(img_array)`. If NumPy array conversion fails, falls back to writing a temporary file with a sanitized auto-generated name (user filename is never used in path resolution).
4. **Thread Offloading**: Calls `await asyncio.to_thread(self._run_inference, ...)` to ensure blocking C++ engine inference does not block the FastAPI event loop.

### 5.2 Defensive Result Parsing

PaddleOCR 3.x outputs can take multiple shapes across versions and configurations. `_parse_paddle_result()` defensively supports three common output structures:
- **3.x Attribute Objects**: Objects containing `.rec_texts`, `.rec_scores`, and `.dt_polys`.
- **Dict Objects**: Lists of dictionaries containing `text`, `score`/`confidence`, and `box`/`bbox`.
- **2.x Legacy Nested Lists**: `[ [ [bbox, (text, score)], ... ] ]`.

### 5.3 Financial Text Preservation

The provider performs **zero post-processing** on text content. No character substitutions (e.g. replacing 'O' with '0' or 'I' with '1') are performed. Financial numbers, currency symbols, and account numbers are passed verbatim to downstream processing layers (such as Claude).

---

## 6. Factory Module (`factory.py`)

The `get_ocr_provider()` function instantiates and returns the configured provider:

```python
from app.providers.ocr import get_ocr_provider

# Resolves from settings.OCR_PROVIDER (default: 'paddleocr')
provider = get_ocr_provider()

# Or specify explicitly:
provider = get_ocr_provider("paddleocr")
```

The returned instance is lightweight and has not yet loaded heavy models into memory.

---

## 7. Configuration Settings

Configured in `app/core/config.py` and `.env.example`:

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `OCR_PROVIDER` | `paddleocr` | Active OCR provider plugin name |
| `OCR_PADDLE_DEVICE` | `auto` | Execution device: `auto`, `cpu`, or `gpu` |
| `OCR_MAX_IMAGE_BYTES` | `20000000` | Maximum image file size in bytes (20 MB) |
| `OCR_MAX_IMAGE_PIXELS` | `50000000` | Maximum allowed image resolution in total pixels |

---

## 8. Dependencies & Installation

`pyproject.toml` includes:
- `pillow>=10.0.0`
- `paddleocr>=3.0.0`

### Installing PaddlePaddle (CPU vs GPU)

PaddlePaddle must be installed from the official Paddle index:

**CPU Environment (Default / Local Dev):**
```bash
pip install paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
pip install -e .
```

**GPU Environment (CUDA Support):**
```bash
pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
pip install -e .
```

---

## 9. Diagnostics & Testing

### 9.1 Environment Inspection Script
Inspects installed dependencies, CUDA detection, and OCR settings without downloading models:
```bash
python scripts/check_ocr_environment.py
```

### 9.2 Real Image Smoke Test Script
Executes local OCR on a real image file and displays reconstructed text, block confidences, and bounding boxes:
```bash
python scripts/ocr_smoke_test.py path/to/receipt.png
```

### 9.3 Running Unit Tests
Unit tests use dependency injection (`PaddleOCRProvider(pipeline=mock_pipeline)`) to run completely offline without model weights or GPU requirements:
```bash
pytest tests/unit/providers/ocr -v
```

---

## 10. Summary of Error Handling & HTTP Mapping

| Exception | Root Cause | Recommended HTTP Response |
| :--- | :--- | :--- |
| `OCRInputError` | Empty bytes, corrupt image, unsupported format, oversized image | `400 Bad Request` or `422 Unprocessable Entity` |
| `OCRConfigurationError` | Unknown provider, GPU requested on CPU machine | `500 Internal Server Error` |
| `OCRModelLoadError` | Model files corrupted or engine failed to start | `503 Service Unavailable` |
| `OCRExtractionError` | Inference runtime crash or no text found in image | `422 Unprocessable Entity` or `500 Internal Server Error` |
