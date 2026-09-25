"""
Real provider smoke test for Quanta Text-to-Speech (TTS) layer.

Usage:
    .venv\\Scripts\\python.exe scripts/tts_smoke_test.py

This script tests real synthesis with Edge TTS and 9jaLingo TTS (if NAIJALINGO_API_KEY is configured),
and saves generated audio files into an output directory.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.services.tts import TTSService

TEST_CASES = [
    {
        "language": "en",
        "gender": "female",
        "text": "Your transfer of five thousand naira was successful.",
        "description": "English Female (Edge TTS)",
    },
    {
        "language": "en",
        "gender": "male",
        "text": "Your account balance has been updated.",
        "description": "English Male (Edge TTS)",
    },
    {
        "language": "ha",
        "gender": "female",
        "text": "Tura kudin ku ya nasara.",
        "description": "Hausa Female (9jaLingo)",
    },
    {
        "language": "ig",
        "gender": "female",
        "text": "Emechaala nnyefe gị nke ọma.",
        "description": "Igbo Female (9jaLingo)",
    },
    {
        "language": "yo",
        "gender": "female",
        "text": "Gbigbe owo re ti pari ni aṣeyọri.",
        "description": "Yoruba Female (9jaLingo)",
    },
    {
        "language": "pcm",
        "gender": "female",
        "text": "Your transfer don complete successfully.",
        "description": "Pidgin Female (9jaLingo)",
    },
]


async def run_smoke_test() -> None:
    output_dir = PROJECT_ROOT / "output_audio"
    output_dir.mkdir(exist_ok=True)

    tts_service = TTSService()
    has_naijalingo_key = bool(settings.NAIJALINGO_API_KEY and settings.NAIJALINGO_API_KEY.strip())

    print("=" * 85)
    print("Quanta TTS Real Provider Smoke Test")
    print("=" * 85)
    print(f"Output Directory : {output_dir}")
    print(
        f"9jaLingo API Key : {'Configured' if has_naijalingo_key else 'NOT Configured (9jaLingo tests will be skipped)'}"
    )
    print("=" * 85)
    print(
        f"{'PROVIDER':<12} {'LANG':<6} {'GENDER':<8} {'VOICE':<22} {'BYTES':<10} {'TIME (s)':<10} {'STATUS'}"
    )
    print("-" * 85)

    results = []

    for test_case in TEST_CASES:
        lang = test_case["language"]
        gender = test_case["gender"]
        text = test_case["text"]

        is_naijalingo = lang in {"ha", "ig", "yo", "pcm"}
        if is_naijalingo and not has_naijalingo_key:
            print(
                f"{'naijalingo':<12} {lang:<6} {gender:<8} {'(skipped)':<22} {'0':<10} {'0.00':<10} SKIPPED (No API key)"
            )
            continue

        start_time = time.perf_counter()
        try:
            result = await tts_service.synthesize(
                text=text,
                language=lang,
                gender=gender,
            )
            elapsed = time.perf_counter() - start_time
            provider_name = result.provider_metadata.get("provider", "unknown")
            voice = result.provider_metadata.get("voice", "unknown")
            byte_count = len(result.audio)

            # Determine file extension based on content_type
            ext = ".mp3" if "mpeg" in result.content_type else ".wav"
            filename = f"tts_{provider_name}_{lang}_{gender}{ext}"
            file_path = output_dir / filename
            file_path.write_bytes(result.audio)

            print(
                f"{provider_name:<12} {lang:<6} {gender:<8} {voice:<22} {byte_count:<10} {elapsed:<10.2f} OK ({filename})"
            )
            results.append((provider_name, lang, voice, byte_count, elapsed, True))
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            elapsed = time.perf_counter() - start_time
            print(
                f"{'error':<12} {lang:<6} {gender:<8} {'FAILED':<22} {'0':<10} {elapsed:<10.2f} ERROR: {exc}"
            )
            results.append(("error", lang, "", 0, elapsed, False))

    print("=" * 85)
    passed_count = sum(1 for r in results if r[5])
    print(f"Smoke test completed: {passed_count}/{len(TEST_CASES)} passed.")
    print("=" * 85)


def main() -> None:
    asyncio.run(run_smoke_test())


if __name__ == "__main__":
    main()
