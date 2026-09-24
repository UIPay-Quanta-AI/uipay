import pytest

from app.providers.tts import (
    TTSConfigurationError,
    VoiceSelection,
    resolve_voice,
)


def test_resolve_voice_english_female():
    selection = resolve_voice(language="en", gender="female")
    assert isinstance(selection, VoiceSelection)
    assert selection.provider == "edge"
    assert selection.voice == "en-NG-EzinneNeural"
    assert selection.language == "en-NG"


def test_resolve_voice_english_male():
    selection = resolve_voice(language="en", gender="male")
    assert selection.provider == "edge"
    assert selection.voice == "en-NG-AbeoNeural"
    assert selection.language == "en-NG"


def test_resolve_voice_hausa():
    female = resolve_voice(language="ha", gender="female")
    assert female.provider == "naijalingo"
    assert female.voice == "maryam_ha"
    assert female.language == "ha"

    male = resolve_voice(language="hausa", gender="male")
    assert male.provider == "naijalingo"
    assert male.voice == "abdullahi_ha"
    assert male.language == "ha"


def test_resolve_voice_igbo():
    female = resolve_voice(language="ig", gender="female")
    assert female.provider == "naijalingo"
    assert female.voice == "obianuju_ig"
    assert female.language == "ig"

    male = resolve_voice(language="igbo", gender="male")
    assert male.provider == "naijalingo"
    assert male.voice == "okechukwu_ig"
    assert male.language == "ig"


def test_resolve_voice_yoruba():
    female = resolve_voice(language="yo", gender="female")
    assert female.provider == "naijalingo"
    assert female.voice == "abisoye_yo"
    assert female.language == "yo"

    male = resolve_voice(language="yoruba", gender="male")
    assert male.provider == "naijalingo"
    assert male.voice == "babatunde_yo"
    assert male.language == "yo"


def test_resolve_voice_pidgin():
    female = resolve_voice(language="pcm", gender="female")
    assert female.provider == "naijalingo"
    assert female.voice == "dora_pcm"
    assert female.language == "pcm"

    male = resolve_voice(language="pidgin", gender="male")
    assert male.provider == "naijalingo"
    assert male.voice == "frank_pcm"
    assert male.language == "pcm"


def test_resolve_voice_unsupported_language():
    with pytest.raises(TTSConfigurationError, match="Unsupported language"):
        resolve_voice(language="fr", gender="female")


def test_resolve_voice_unsupported_gender():
    with pytest.raises(TTSConfigurationError, match="Unsupported gender"):
        resolve_voice(language="en", gender="non-binary")
