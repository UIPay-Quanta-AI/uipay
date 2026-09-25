from __future__ import annotations

import asyncio
import io
import logging
import tempfile
import time
from typing import Any

from app.providers.ocr.base import (
    OCRExtractionError,
    OCRModelLoadError,
    OCRProvider,
    OCRResult,
    OCRTextBlock,
)
from app.providers.ocr.image import validate_image

# On Windows environments, pre-loading PyTorch C++ DLLs prevents WinError 127 procedure conflicts
# when Paddle C++ DLLs and PyTorch DLLs are loaded into the same process.
try:
    import torch  # type: ignore[import-untyped]  # noqa: F401
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Device resolution
# ---------------------------------------------------------------------------


def resolve_paddle_device(device_setting: str) -> str:
    """
    Resolve the OCR_PADDLE_DEVICE setting to a concrete PaddleOCR device string.

    Supported values:
    - "auto"  → use GPU if available, otherwise CPU
    - "cpu"   → force CPU
    - "gpu"   → require GPU; raise OCRConfigurationError if unavailable

    PaddleOCR's pipeline accepts "cpu" or "gpu" (not "cuda").
    """
    from app.providers.ocr.base import OCRConfigurationError

    cleaned = device_setting.strip().lower()

    if cleaned == "cpu":
        return "cpu"

    # GPU availability check via paddle
    if cleaned in {"gpu", "auto"}:
        try:
            import paddle  # type: ignore[import-untyped]

            gpu_available = paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
        except Exception:  # noqa: BLE001
            gpu_available = False

        if cleaned == "gpu":
            if not gpu_available:
                raise OCRConfigurationError(
                    "GPU device was explicitly requested for PaddleOCR, "
                    "but no CUDA-capable GPU was detected."
                )
            return "gpu"

        # auto
        return "gpu" if gpu_available else "cpu"

    from app.providers.ocr.base import OCRConfigurationError

    raise OCRConfigurationError(
        f"Invalid OCR_PADDLE_DEVICE setting '{device_setting}'. Expected 'auto', 'cpu', or 'gpu'."
    )


# ---------------------------------------------------------------------------
# PaddleOCR result parsing
# ---------------------------------------------------------------------------


def _parse_paddle_result(raw_result: Any) -> list[OCRTextBlock]:
    """
    Convert PaddleOCR 3.x predict() output into a list of OCRTextBlock objects.

    PaddleOCR 3.x returns a list of result objects per page. For each page
    the relevant fields are typically:
        rec_texts    – list[str]
        rec_scores   – list[float]
        dt_polys     – list of polygon arrays, shape (4, 2) each

    In PaddleOCR 3.7.0 (PaddleX backend), each page result is a dict subclass
    containing 'rec_texts', 'rec_scores', and 'dt_polys' keys.

    All parsing is isolated here so that changes in PaddleOCR's output format
    only require changes in this function, nowhere else in the application.
    """
    blocks: list[OCRTextBlock] = []

    if raw_result is None:
        return blocks

    if isinstance(raw_result, list) and raw_result:
        for item in raw_result:
            if isinstance(item, list):
                # Wrapped list per page or legacy 2.x list
                for subitem in item:
                    page_blocks = _extract_page_blocks(subitem)
                    if page_blocks:
                        blocks.extend(page_blocks)
                    elif isinstance(subitem, (list, tuple)):
                        blocks.extend(_parse_legacy_results([[subitem]]))
            else:
                page_blocks = _extract_page_blocks(item)
                if page_blocks:
                    blocks.extend(page_blocks)
                elif isinstance(item, dict) and "text" in item:
                    blocks.extend(_parse_dict_results([item]))

    return blocks


def _extract_page_blocks(page: Any) -> list[OCRTextBlock]:
    """Extract OCRTextBlock objects from a single page result (attribute object or dict)."""
    blocks: list[OCRTextBlock] = []
    texts: list[str] = []
    scores: list[float] = []
    polys: list[Any] = []

    if isinstance(page, dict):
        texts = list(page.get("rec_texts") or page.get("texts") or [])
        scores = list(page.get("rec_scores") or page.get("scores") or [])
        polys = list(page.get("dt_polys") or page.get("rec_polys") or page.get("polys") or [])
    else:
        texts = list(getattr(page, "rec_texts", []) or [])
        scores = list(getattr(page, "rec_scores", []) or [])
        polys = list(getattr(page, "dt_polys", []) or getattr(page, "rec_polys", []) or [])

    for idx, text in enumerate(texts):
        stripped = (
            text.strip() if isinstance(text, str) else str(text).strip() if text is not None else ""
        )
        if not stripped:
            continue

        conf: float | None = None
        if idx < len(scores) and scores[idx] is not None:
            try:
                conf = float(scores[idx])
                conf = max(0.0, min(1.0, conf))
            except (TypeError, ValueError):
                conf = None

        bbox: list[list[float]] | None = None
        if idx < len(polys) and polys[idx] is not None:
            bbox = _normalize_polygon(polys[idx])

        blocks.append(OCRTextBlock(text=stripped, confidence=conf, bbox=bbox))

    return blocks


def _parse_dict_results(items: list[dict[str, Any]]) -> list[OCRTextBlock]:
    """Parse result items that are plain dicts."""
    blocks: list[OCRTextBlock] = []
    for item in items:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        conf_raw = item.get("confidence") or item.get("score")
        conf: float | None = None
        if conf_raw is not None:
            try:
                conf = float(conf_raw)
                conf = max(0.0, min(1.0, conf))
            except (TypeError, ValueError):
                pass
        bbox_raw = item.get("bbox") or item.get("box") or item.get("polygon")
        bbox = _normalize_polygon(bbox_raw) if bbox_raw is not None else None
        blocks.append(OCRTextBlock(text=text, confidence=conf, bbox=bbox))
    return blocks


def _parse_legacy_results(pages: list[Any]) -> list[OCRTextBlock]:
    """
    Parse PaddleOCR 2.x legacy format:
        [ [  [bbox, (text, score)], ... ] ]
    """
    blocks: list[OCRTextBlock] = []
    for page in pages:
        if not isinstance(page, list):
            continue
        for line in page:
            if not isinstance(line, (list, tuple)) or len(line) < 2:
                continue
            bbox_raw, rec = line[0], line[1]
            if isinstance(rec, (list, tuple)) and len(rec) >= 2:
                text = str(rec[0]).strip()
                conf_raw = rec[1]
            else:
                text = str(rec).strip()
                conf_raw = None

            if not text:
                continue

            conf: float | None = None
            if conf_raw is not None:
                try:
                    conf = float(conf_raw)
                    conf = max(0.0, min(1.0, conf))
                except (TypeError, ValueError):
                    pass

            bbox = _normalize_polygon(bbox_raw) if bbox_raw is not None else None
            blocks.append(OCRTextBlock(text=text, confidence=conf, bbox=bbox))

    return blocks


def _normalize_polygon(raw: Any) -> list[list[float]] | None:
    """
    Convert a raw polygon from PaddleOCR into [[x0,y0],[x1,y1],[x2,y2],[x3,y3]].

    Accepts numpy arrays, lists of lists, lists of tuples, etc.
    Returns None if conversion fails to avoid crashing on unexpected shapes.
    """
    try:
        # numpy array or list of arrays / tuples
        corners: list[list[float]] = []
        for point in raw:
            if hasattr(point, "__iter__"):
                coords = [float(v) for v in point]
            else:
                coords = [float(point)]
            if len(coords) >= 2:
                corners.append([coords[0], coords[1]])
        if len(corners) >= 3:
            return corners
    except Exception:  # noqa: BLE001, S110
        pass
    return None


def _blocks_to_text(blocks: list[OCRTextBlock]) -> str:
    """
    Join block texts into a full-page string with newlines.

    Each block represents one detected text line.  We join them with "\n" to
    preserve the line structure that Claude and later extraction layers rely on.
    Consecutive blank lines are collapsed to a single blank line.
    Leading/trailing whitespace is removed from the overall result.
    """
    lines = [b.text.strip() for b in blocks]
    # Collapse multiple consecutive blank lines to one
    result_lines: list[str] = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                result_lines.append("")
            prev_blank = True
        else:
            result_lines.append(line)
            prev_blank = False

    return "\n".join(result_lines).strip()


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class PaddleOCRProvider(OCRProvider):
    """
    Primary OCR provider using PaddleOCR 3.x local inference.

    Key design decisions
    --------------------
    Lazy loading
        The PaddleOCR pipeline is NOT initialised at construction time.
        It is initialised on the first call to extract().  This prevents
        model downloads or heavy initialisation from happening merely because
        the provider module is imported.

    Async boundary
        PaddleOCR inference is blocking.  extract() offloads the inference
        call to a thread via asyncio.to_thread() so the FastAPI event loop
        is not stalled.

    In-memory image passing
        We prefer passing image bytes directly to the PaddleOCR pipeline
        without writing a temporary file.  If the pipeline requires a file
        path (common in 3.x), we use a NamedTemporaryFile with a safe
        auto-generated name — the user-supplied filename is never used as
        a filesystem path.

    Financial-text preservation
        This provider performs NO post-processing on recognised text.
        Account numbers, currency symbols, and digits are returned exactly
        as PaddleOCR produced them.  Semantic interpretation belongs to the
        Claude layer.
    """

    def __init__(
        self,
        *,
        device: str = "auto",
        max_image_bytes: int | None = None,
        max_image_pixels: int | None = None,
        # Injected for unit testing; None means lazy-create on first extract()
        pipeline: Any | None = None,
    ) -> None:
        self.device_setting = device
        self.max_image_bytes = max_image_bytes
        self.max_image_pixels = max_image_pixels

        self._resolved_device: str | None = None
        self._pipeline: Any | None = pipeline
        self._lock = asyncio.Lock()

    @property
    def resolved_device(self) -> str:
        if self._resolved_device is None:
            self._resolved_device = resolve_paddle_device(self.device_setting)
        return self._resolved_device

    def _ensure_loaded(self) -> None:
        """
        Lazy-initialise the PaddleOCR pipeline if not already loaded.

        This is called inside the asyncio.Lock so only one initialisation
        can proceed at a time even if concurrent extract() calls arrive.
        """
        if self._pipeline is not None:
            return

        device = self.resolved_device

        try:
            # On Windows, pre-loading PyTorch C++ DLLs prevents WinError 127 procedure conflicts
            try:
                import torch  # type: ignore[import-untyped]  # noqa: F401
            except ImportError:
                pass

            from paddleocr import PaddleOCR  # type: ignore[import-untyped]

            # We use the general OCR pipeline with optional modules disabled
            # to keep the footprint lean for our arbitrary-image use case.
            # doc_orientation_classify, doc_unwarping, textline_orientation
            # are disabled because our initial use case is clean screenshots.
            # These can be enabled later if smoke tests on rotated/skewed
            # images show they are needed.
            self._pipeline = PaddleOCR(
                device=device,
                # Disable heavyweight optional modules not needed for
                # general OCR of account-detail screenshots.
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        except OCRModelLoadError:
            raise
        except Exception as exc:
            raise OCRModelLoadError(
                f"Failed to initialise PaddleOCR pipeline (device={device}): {exc}"
            ) from exc

    def _run_inference(self, image_bytes: bytes) -> Any:
        """
        Blocking OCR inference.  Always runs in a thread via asyncio.to_thread().

        PaddleOCR 3.x predict() can accept a numpy array or a file path.
        We prefer numpy (in-memory) to avoid touching the filesystem.
        If numpy is unavailable or predict() rejects the array, we fall back
        to a safe temporary file with a sanitised name.
        """
        assert self._pipeline is not None

        # Attempt 1: numpy array (no filesystem involvement)
        try:
            import numpy as np
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_array = np.array(img)
            return self._pipeline.predict(img_array)
        except Exception as numpy_exc:  # noqa: BLE001
            logger.debug("In-memory numpy path failed (%s); trying temp-file path.", numpy_exc)

        # Attempt 2: safe temporary file — user filename is never used
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                import os

                tmp.write(image_bytes)
                tmp_path = tmp.name
            try:
                return self._pipeline.predict(tmp_path)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        except Exception as exc:
            raise OCRExtractionError(
                f"PaddleOCR inference failed via both numpy and temp-file paths: {exc}"
            ) from exc

    async def extract(
        self,
        *,
        image: bytes,
        filename: str | None = None,
    ) -> OCRResult:
        """
        Extract text from an image using PaddleOCR local inference.
        """
        # --- Image validation (fast, synchronous) ---------------------------
        validated = validate_image(
            image,
            max_bytes=self.max_image_bytes,
            max_pixels=self.max_image_pixels,
        )

        logger.info(
            "OCR extraction started: format=%s size=%dx%d bytes=%d",
            validated.format,
            validated.width,
            validated.height,
            len(image),
        )

        # --- Lazy model init (inside lock to prevent concurrent downloads) --
        async with self._lock:
            self._ensure_loaded()

        pipeline = self._pipeline
        assert pipeline is not None

        # --- Blocking inference offloaded to thread -------------------------
        t0 = time.monotonic()
        try:
            raw_result = await asyncio.to_thread(self._run_inference, validated.data)
        except OCRExtractionError:
            raise
        except Exception as exc:
            raise OCRExtractionError(f"PaddleOCR extraction failed: {exc}") from exc
        elapsed = time.monotonic() - t0

        # --- Parse & normalise result ---------------------------------------
        try:
            blocks = _parse_paddle_result(raw_result)
        except Exception as exc:
            raise OCRExtractionError(f"Failed to parse PaddleOCR result: {exc}") from exc

        if not blocks:
            # PaddleOCR found no text in this image.  Return a meaningful
            # placeholder so callers receive a valid OCRResult rather than
            # raising.  An empty image is technically valid (the OCR just
            # found nothing).
            # We raise here because OCRResult requires text min_length=1.
            raise OCRExtractionError("PaddleOCR found no text in the provided image.")

        full_text = _blocks_to_text(blocks)
        if not full_text:
            raise OCRExtractionError("PaddleOCR produced only whitespace-only text blocks.")

        logger.info(
            "OCR extraction complete: blocks=%d elapsed=%.2fs",
            len(blocks),
            elapsed,
        )

        return OCRResult(
            text=full_text,
            blocks=blocks,
            provider="paddleocr",
            provider_metadata={
                "device": self.resolved_device,
                "elapsed_seconds": f"{elapsed:.3f}",
                "image_format": validated.format,
                "image_size": f"{validated.width}x{validated.height}",
                "filename": filename or "",
            },
        )
