#!/usr/bin/env python3
"""
Real Image Smoke Test Script for Quanta OCR Subsystem.

Reads an image file and extracts text using the specified or configured OCR provider.
This script DOES NOT invoke UI Pay, Claude LLM, or financial transfer tools.

Usage:
    python scripts/ocr_smoke_test.py path/to/image.png
    python scripts/ocr_smoke_test.py path/to/image.jpg --provider paddleocr
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure quanta project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.core.config import settings
from app.providers.ocr import get_ocr_provider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run image file through Quanta OCR provider.")
    parser.add_argument(
        "image_path",
        type=str,
        help="Path to input image file (PNG, JPEG, WEBP)",
    )
    parser.add_argument(
        "--provider",
        choices=["paddleocr"],
        default=None,
        help="OCR provider to use (default: from OCR_PROVIDER setting)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    file_path = Path(args.image_path)

    if not file_path.is_file():
        print(f"Error: Image file not found at '{file_path}'", file=sys.stderr)
        sys.exit(1)

    print(f"Reading image file: {file_path}")
    image_bytes = file_path.read_bytes()

    provider_name = args.provider or settings.OCR_PROVIDER
    print(f"Initializing OCR provider: '{provider_name}'...")
    provider = get_ocr_provider(provider_name=provider_name)

    print(f"Extracting text ({len(image_bytes):,} bytes)...")
    try:
        result = await provider.extract(
            image=image_bytes,
            filename=file_path.name,
        )

        print("\n" + "=" * 60)
        print("OCR EXTRACTION RESULT")
        print("=" * 60)
        print(f"Provider: {result.provider}")
        print(f"Metadata: {result.provider_metadata}")
        print("-" * 60)
        print("FULL RECONSTRUCTED TEXT:")
        print(result.text)
        print("-" * 60)
        print(f"DETAILED BLOCKS ({len(result.blocks)} detected):")
        for i, block in enumerate(result.blocks, start=1):
            conf_str = f"{block.confidence:.2f}" if block.confidence is not None else "N/A"
            bbox_str = str(block.bbox) if block.bbox else "None"
            print(f"  [{i:02d}] Text:       '{block.text}'")
            print(f"       Confidence: {conf_str}")
            print(f"       BoundingBox: {bbox_str}")
        print("=" * 60)

    except Exception as exc:  # noqa: BLE001
        print(f"\nOCR Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
