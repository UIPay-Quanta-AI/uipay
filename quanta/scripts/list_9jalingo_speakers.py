"""
List available 9jaLingo speakers for Quanta voice selection.

This is a one-off/setup utility, not part of Quanta's runtime TTS architecture.

Usage:
    python scripts/list_9jalingo_speakers.py

The script reads NAIJALINGO_API_KEY through Quanta's shared Settings
configuration, which loads values from the project's .env file.
"""

from __future__ import annotations

from naijalingo import NaijaLingo

from app.core.config import Settings

LANGUAGES = {
    "ha": "Hausa",
    "ig": "Igbo",
    "yo": "Yoruba",
    "pcm": "Nigerian Pidgin",
}


def main() -> None:
    settings = Settings()

    if not settings.NAIJALINGO_API_KEY:
        raise RuntimeError("NAIJALINGO_API_KEY is not configured in .env.")

    client = NaijaLingo(api_key=settings.NAIJALINGO_API_KEY)

    print("=" * 80)
    print("9jaLingo Speaker Discovery")
    print("=" * 80)

    for language_code, language_name in LANGUAGES.items():
        print(f"\n{'=' * 80}")
        print(f"{language_name} ({language_code})")
        print("=" * 80)

        try:
            speakers = client.tts.list_speakers(language=language_code)
        except (OSError, RuntimeError, ValueError) as exc:
            print(f"ERROR: Could not fetch speakers: {exc}")
            continue

        if not speakers:
            print("No speakers returned.")
            continue

        print(f"Found {len(speakers)} speaker(s).\n")

        for index, speaker in enumerate(speakers, start=1):
            print(f"--- Speaker {index} ---")

            if hasattr(speaker, "model_dump"):
                data = speaker.model_dump()

                for key, value in data.items():
                    print(f"{key}: {value}")
            else:
                print(f"id: {getattr(speaker, 'id', None)}")
                print(f"name: {getattr(speaker, 'name', None)}")
                print(f"language: {getattr(speaker, 'language', None)}")
                print(f"gender: {getattr(speaker, 'gender', None)}")
                print(f"details: {speaker}")

            print()

    print("=" * 80)
    print("Speaker discovery complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
