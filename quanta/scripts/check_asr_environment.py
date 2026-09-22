#!/usr/bin/env python3
"""
Diagnostic script for inspecting Quanta ASR environment dependencies and settings.
Does NOT download heavyweight models.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure quanta project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

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
    print("QUANTA ASR ENVIRONMENT DIAGNOSTICS")
    print("=" * 60)
    print(f"Python Version: {sys.version.split()[0]}")

    print("\n--- Package Dependencies ---")
    packages = [
        ("PyTorch", "torch"),
        ("Transformers", "transformers"),
        ("HuggingFace Hub", "huggingface_hub"),
        ("faster-whisper", "faster_whisper"),
        ("PyAV", "av"),
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
        import torch

        cuda_ok = torch.cuda.is_available()
        print(f"  CUDA Available: {cuda_ok}")
        if cuda_ok:
            print(f"  CUDA Device:    {torch.cuda.get_device_name(0)}")
            print(f"  CUDA Version:   {torch.version.cuda}")
    except ImportError:
        print("  CUDA Check:     PyTorch not installed")

    print("\n--- ASR Settings ---")
    print(f"  ASR_PROVIDER:             {settings.ASR_PROVIDER}")
    print(f"  ASR_MAX_AUDIO_BYTES:      {settings.ASR_MAX_AUDIO_BYTES:,} bytes")
    print(f"  ASR_MAX_DURATION_SECONDS: {settings.ASR_MAX_DURATION_SECONDS}s")
    print(f"  ASR_NAIJAVOX_MODEL_ID:    {settings.ASR_NAIJAVOX_MODEL_ID}")
    print(f"  ASR_NAIJAVOX_DEVICE:      {settings.ASR_NAIJAVOX_DEVICE}")
    print(f"  ASR_FASTER_WHISPER_MODEL: {settings.ASR_FASTER_WHISPER_MODEL}")
    print(f"  ASR_FASTER_WHISPER_DEVICE:{settings.ASR_FASTER_WHISPER_DEVICE}")

    print("\n" + "=" * 60)
    if all_ok:
        print("STATUS: All ASR dependencies are present.")
    else:
        print("STATUS: Some dependencies are missing. Run pip install -e .")
    print("=" * 60)


if __name__ == "__main__":
    main()
