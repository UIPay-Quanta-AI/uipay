from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.providers.tts.base import TTSConfigurationError

Gender = Literal["female", "male"]
LanguageCode = Literal["en", "ha", "ig", "yo", "pcm"]


DEFAULT_VOICES = {
    "en": {
        "female": {
            "provider": "edge",
            "voice": "en-NG-EzinneNeural",
        },
        "male": {
            "provider": "edge",
            "voice": "en-NG-AbeoNeural",
        },
    },
    "ha": {
        "female": {
            "provider": "naijalingo",
            "voice": "maryam_ha",
        },
        "male": {
            "provider": "naijalingo",
            "voice": "abdullahi_ha",
        },
    },
    "ig": {
        "female": {
            "provider": "naijalingo",
            "voice": "obianuju_ig",
        },
        "male": {
            "provider": "naijalingo",
            "voice": "okechukwu_ig",
        },
    },
    "yo": {
        "female": {
            "provider": "naijalingo",
            "voice": "abisoye_yo",
        },
        "male": {
            "provider": "naijalingo",
            "voice": "babatunde_yo",
        },
    },
    "pcm": {
        "female": {
            "provider": "naijalingo",
            "voice": "dora_pcm",
        },
        "male": {
            "provider": "naijalingo",
            "voice": "frank_pcm",
        },
    },
}


class VoiceSelection(BaseModel):
    """
    Result of voice resolution mapping (language, gender) to provider and speaker ID.
    """

    provider: str = Field(min_length=1)
    voice: str = Field(min_length=1)
    language: str = Field(min_length=1)


def resolve_voice(
    language: str,
    gender: str = "female",
) -> VoiceSelection:
    """
    Resolve requested language and gender preference into provider and voice ID.

    Normalizes language codes:
    - 'en', 'en-NG', 'en_NG', 'english' -> 'en'
    - 'ha', 'hausa', 'ha-NG' -> 'ha'
    - 'ig', 'igbo', 'ig-NG' -> 'ig'
    - 'yo', 'yoruba', 'yo-NG' -> 'yo'
    - 'pcm', 'pidgin', 'naija pidgin', 'pcm-NG' -> 'pcm'

    Raises TTSConfigurationError for unsupported language or gender.
    """
    norm_lang = (language or "").strip().lower()
    if norm_lang in {"en", "en-ng", "en_ng", "english"}:
        norm_lang = "en"
    elif norm_lang in {"ha", "hausa", "ha-ng", "ha_ng"}:
        norm_lang = "ha"
    elif norm_lang in {"ig", "igbo", "ig-ng", "ig_ng"}:
        norm_lang = "ig"
    elif norm_lang in {"yo", "yoruba", "yo-ng", "yo_ng"}:
        norm_lang = "yo"
    elif norm_lang in {"pcm", "pidgin", "pcm-ng", "pcm_ng", "naija pidgin"}:
        norm_lang = "pcm"

    norm_gender = (gender or "").strip().lower()
    if norm_gender not in {"female", "male"}:
        raise TTSConfigurationError(
            f"Unsupported gender '{gender}'. Supported genders: 'female', 'male'."
        )

    lang_voices = DEFAULT_VOICES.get(norm_lang)
    if not lang_voices:
        raise TTSConfigurationError(
            f"Unsupported language '{language}'. Supported languages: {list(DEFAULT_VOICES.keys())}."
        )

    selection = lang_voices.get(norm_gender)
    if not selection:
        raise TTSConfigurationError(f"Unsupported gender '{gender}' for language '{language}'.")

    # For Edge TTS, map application 'en' to provider voice language 'en-NG'
    target_language = "en-NG" if selection["provider"] == "edge" else norm_lang

    return VoiceSelection(
        provider=selection["provider"],
        voice=selection["voice"],
        language=target_language,
    )
