#!/usr/bin/env python3
"""
Diagnostic script for inspecting Quanta OCR environment dependencies and settings.
Does NOT download heavyweight models or run inference.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure quanta project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# On Windows environments, pre-importing torch ensures PyTorch DLLs initialize
# before Paddle C++ runtime, preventing WinError 127 DLL procedure conflicts.
try:
    import torch  # type: ignore[import-untyped]  # noqa: F401
except ImportError:
    pass

from app.core.config import settings


def check_package(name: str, import_name: str | None = None) -> tuple[bool, str]:
    mod_name = import_name or name
    try:
        mod = __import__(mod_name)
        ver = getattr(mod, "__version__", "installed")
        return True, str(ver)
    except ImportError:
        return False, "not installed"


def main() -> None:
    print("=" * 60)
    print("QUANTA OCR ENVIRONMENT DIAGNOSTICS")
    print("=" * 60)
    print(f"Python Version: {sys.version.split()[0]}")

    print("\n--- Package Dependencies ---")
    packages = [
        ("PaddlePaddle", "paddle"),
        ("PaddleOCR", "paddleocr"),
        ("Pillow", "PIL"),
        ("NumPy", "numpy"),
    ]

    all_ok = True
    for display_name, import_name in packages:
        ok, ver = check_package(display_name, import_name)
        status = "OK" if ok else "MISSING"
        print(f"  [{status:7}] {display_name:20}: {ver}")
        if not ok:
            all_ok = False

    print("\n--- Hardware / Acceleration ---")
    try:
        import paddle  # type: ignore[import-untyped]

        cuda_ok = paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
        print(f"  CUDA Compiled:  {paddle.is_compiled_with_cuda()}")
        print(f"  CUDA Available: {cuda_ok}")
        if cuda_ok:
            print(f"  CUDA Device:    {paddle.device.cuda.get_device_name(0)}")
    except Exception as exc:  # noqa: BLE001
        print(f"  CUDA Check:     PaddlePaddle check failed ({exc})")

    print("\n--- OCR Settings ---")
    print(f"  OCR_PROVIDER:         {settings.OCR_PROVIDER}")
    print(f"  OCR_PADDLE_DEVICE:    {settings.OCR_PADDLE_DEVICE}")
    print(f"  OCR_MAX_IMAGE_BYTES:  {settings.OCR_MAX_IMAGE_BYTES:,} bytes")
    print(f"  OCR_MAX_IMAGE_PIXELS: {settings.OCR_MAX_IMAGE_PIXELS:,} pixels")

    print("\n" + "=" * 60)
    if all_ok:
        print("STATUS: All OCR dependencies are present.")
    else:
        print("STATUS: Some dependencies are missing.")
        print("Note: Install official project dependencies using:")
        print("      pip install -e .")
    print("=" * 60)


if __name__ == "__main__":
    main()
