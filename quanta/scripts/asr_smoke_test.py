#!/usr/bin/env python3
"""
Real Audio Smoke Test Script for Quanta ASR Subsystem.

Reads an audio file and transcribes it using the specified or configured ASR provider.
This script DOES NOT invoke UI Pay, Claude LLM, or financial transfer tools.

Usage:
    python scripts/asr_smoke_test.py path/to/audio.wav
    python scripts/asr_smoke_test.py path/to/audio.mp3 --provider naijavox --language pcm
    python scripts/asr_smoke_test.py path/to/audio.m4a --provider faster_whisper --language yo
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
from app.providers.asr import get_asr_provider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real audio file through Quanta ASR provider.")
    parser.add_argument(
        "audio_path",
        type=str,
        help="Path to input audio file (WAV, MP3, M4A, WebM, etc.)",
    )
    parser.add_argument(
        "--provider",
        choices=["naijavox", "faster_whisper"],
        default=None,
        help="ASR provider to use (default: from ASR_PROVIDER setting)",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language hint/code (e.g., pcm, yo, ha, ig, en)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    file_path = Path(args.audio_path)

    if not file_path.is_file():
        print(f"Error: Audio file not found at '{file_path}'", file=sys.stderr)
        sys.exit(1)

    print(f"Reading audio file: {file_path}")
    audio_bytes = file_path.read_bytes()

    provider_name = args.provider or settings.ASR_PROVIDER
    print(f"Initializing ASR provider: '{provider_name}'...")
    provider = get_asr_provider(provider_name=provider_name)

    print(f"Transcribing ({len(audio_bytes)} bytes, language={args.language or 'auto'})...")
    try:
        result = await provider.transcribe(
            audio=audio_bytes,
            filename=file_path.name,
            language=args.language,
        )

        print("\n" + "=" * 50)
        print("ASR TRANSCRIPTION RESULT")
        print("=" * 50)
        print(f"Text:       {result.text}")
        print(f"Language:   {result.language}")
        print(
            f"Duration:   {result.duration_seconds:.2f}s"
            if result.duration_seconds
            else "Duration: N/A"
        )
        print(f"Provider:   {result.provider}")
        print(f"Metadata:   {result.metadata}")
        print("=" * 50)

    except Exception as exc:  # noqa: BLE001
        print(f"\nASR Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
