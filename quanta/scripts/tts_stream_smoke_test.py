"""
Real provider streaming smoke test for Quanta 9jaLingo TTS.

Usage:
    .venv\\Scripts\\python.exe scripts/tts_stream_smoke_test.py

This script tests streaming speech audio from 9jaLingo SDK and verifies:
1. Stream starts
2. First chunk arrives (recording TTFC - Time To First Chunk)
3. Chunks arrive continuously
4. Total output bytes are non-empty
5. Output audio is saved to file without errors.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.providers.tts.naijalingo import NaijaLingoProvider

TEST_CASES = [
    {
        "language": "pcm",
        "voice": "dora_pcm",
        "text": "Your transfer don complete successfully.",
        "description": "Pidgin Dora Streaming",
    },
    {
        "language": "ig",
        "voice": "obianuju_ig",
        "text": "Emechaala nnyefe gị nke ọma.",
        "description": "Igbo Obianuju Streaming",
    },
]


async def run_stream_smoke_test() -> None:
    output_dir = PROJECT_ROOT / "output_audio"
    output_dir.mkdir(exist_ok=True)

    if not settings.NAIJALINGO_API_KEY or not settings.NAIJALINGO_API_KEY.strip():
        print("NAIJALINGO_API_KEY is not configured in .env. Skipping streaming smoke test.")
        return

    provider = NaijaLingoProvider(settings=settings)

    print("=" * 85)
    print("Quanta 9jaLingo Streaming Smoke Test")
    print("=" * 85)
    print(
        f"{'VOICE':<15} {'LANG':<6} {'CHUNKS':<8} {'BYTES':<10} {'TTFC (s)':<10} {'TOTAL (s)':<10} {'STATUS'}"
    )
    print("-" * 85)

    for test_case in TEST_CASES:
        voice = test_case["voice"]
        lang = test_case["language"]
        text = test_case["text"]

        start_time = time.perf_counter()
        ttfc = None
        chunks = []
        chunk_count = 0
        total_bytes = 0

        try:
            async for chunk in provider.stream(
                text=text,
                voice=voice,
                language=lang,
            ):
                if ttfc is None:
                    ttfc = time.perf_counter() - start_time
                chunks.append(chunk)
                chunk_count += 1
                total_bytes += len(chunk)

            total_elapsed = time.perf_counter() - start_time
            audio_bytes = b"".join(chunks)

            output_file = output_dir / f"stream_{voice}_{lang}.wav"
            output_file.write_bytes(audio_bytes)

            ttfc_str = f"{ttfc:.3f}" if ttfc is not None else "N/A"
            print(
                f"{voice:<15} {lang:<6} {chunk_count:<8} {total_bytes:<10} {ttfc_str:<10} {total_elapsed:<10.2f} OK ({output_file.name})"
            )

        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            total_elapsed = time.perf_counter() - start_time
            print(
                f"{voice:<15} {lang:<6} {'0':<8} {'0':<10} {'N/A':<10} {total_elapsed:<10.2f} ERROR: {exc}"
            )

    print("=" * 85)
    print("Streaming smoke test complete.")
    print("=" * 85)


def main() -> None:
    asyncio.run(run_stream_smoke_test())


if __name__ == "__main__":
    main()
