from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from app.providers.ocr.base import OCRInputError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported formats
# ---------------------------------------------------------------------------

# Pillow reports format names like "PNG", "JPEG", "WEBP".
# This is the allow-list for formats we explicitly support.
# Other formats that Pillow can decode are tolerated only if they produce a
# valid image; we do not enumerate every possible format.
_SUPPORTED_FORMATS: frozenset[str] = frozenset({"PNG", "JPEG", "WEBP"})


# ---------------------------------------------------------------------------
# Validated image representation
# ---------------------------------------------------------------------------


@dataclass
class ValidatedImage:
    """
    A decoded, validated image ready for PaddleOCR.

    data   – Original image bytes (unchanged; we do NOT mutate uploaded data).
    width  – Pixel width of the decoded image.
    height – Pixel height of the decoded image.
    format – Normalised Pillow format string, e.g. "PNG", "JPEG".
    mode   – Pillow colour mode of the decoded image, e.g. "RGB", "L".
    """

    data: bytes
    width: int
    height: int
    format: str
    mode: str

    @property
    def pixel_count(self) -> int:
        return self.width * self.height


# ---------------------------------------------------------------------------
# Public validation entry-point
# ---------------------------------------------------------------------------


def validate_image(
    image: bytes,
    *,
    max_bytes: int | None = None,
    max_pixels: int | None = None,
) -> ValidatedImage:
    """
    Validate raw image bytes and return a :class:`ValidatedImage`.

    This function:
    - Rejects empty bytes.
    - Rejects payloads that exceed *max_bytes*.
    - Decodes the image with Pillow to verify the bytes are genuine image data.
    - Rejects formats not in *_SUPPORTED_FORMATS*.
    - Rejects images with more pixels than *max_pixels*.

    The original bytes are NOT modified.  PaddleOCR will receive them as-is
    (or via a safe in-memory buffer if it requires a file-like object).

    Security note
    -------------
    We do NOT trust *filename* (not accepted here — callers must strip it).
    We validate by decoding with Pillow, not by inspecting magic bytes or
    filename extensions, which are trivially spoofable.
    """
    if not image:
        raise OCRInputError("Image input is empty.")

    if max_bytes is not None and len(image) > max_bytes:
        raise OCRInputError(
            f"Image payload size ({len(image):,} bytes) exceeds the configured "
            f"limit ({max_bytes:,} bytes)."
        )

    # Attempt to import Pillow.  It is a required dependency; raise clearly if
    # it is somehow absent rather than producing a confusing AttributeError.
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise OCRInputError(
            "Pillow is required for image validation but is not installed. Run: pip install pillow"
        ) from exc

    # Decode with Pillow.  This is the canonical format-validation step.
    try:
        img = Image.open(io.BytesIO(image))
        # Force Pillow to actually read the compressed data so corrupt images
        # are caught here rather than later inside PaddleOCR.
        img.verify()
    except UnidentifiedImageError as exc:
        raise OCRInputError(f"Image format is not recognised or supported: {exc}") from exc
    except Exception as exc:
        raise OCRInputError(f"Image data is corrupt or unreadable: {exc}") from exc

    # After verify() the internal image state is consumed; re-open to read
    # metadata (Pillow's verify() exhausts the stream).
    try:
        img = Image.open(io.BytesIO(image))
    except Exception as exc:
        raise OCRInputError(f"Failed to re-open image after validation: {exc}") from exc

    fmt = (img.format or "").upper()
    # JPEG files sometimes report as "MPO" (Multi-Picture Object); treat as JPEG.
    if fmt == "MPO":
        fmt = "JPEG"

    if fmt not in _SUPPORTED_FORMATS:
        raise OCRInputError(
            f"Image format '{fmt}' is not supported. "
            f"Supported formats: {', '.join(sorted(_SUPPORTED_FORMATS))}."
        )

    width, height = img.size
    pixel_count = width * height

    if max_pixels is not None and pixel_count > max_pixels:
        raise OCRInputError(
            f"Image pixel count ({pixel_count:,} px, {width}×{height}) exceeds "
            f"the configured limit ({max_pixels:,} px)."
        )

    logger.debug(
        "Image validated: format=%s mode=%s size=%dx%d bytes=%d",
        fmt,
        img.mode,
        width,
        height,
        len(image),
    )

    return ValidatedImage(
        data=image,
        width=width,
        height=height,
        format=fmt,
        mode=img.mode,
    )
