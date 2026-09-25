from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings as default_settings
from app.providers.tts.base import TTSProvider, TTSResult
from app.providers.tts.factory import get_tts_provider
from app.providers.tts.voices import resolve_voice

if TYPE_CHECKING:
    from app.core.config import Settings


class TTSService:
    """
    Orchestration service for Text-to-Speech synthesis.

    Takes high-level parameters (text, response language, gender preference),
    resolves the appropriate voice speaker and provider, and delegates synthesis
    to the target TTSProvider.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        provider: TTSProvider | None = None,
    ) -> None:
        self.settings = settings or default_settings
        self._override_provider = provider

    async def synthesize(
        self,
        *,
        text: str,
        language: str = "en",
        gender: str | None = None,
    ) -> TTSResult:
        """
        Synthesize text into speech.

        Args:
            text: Response text to convert to speech.
            language: Canonical language code ('en', 'ha', 'ig', 'yo', 'pcm').
            gender: Gender preference ('female' or 'male'). Defaults to TTS_DEFAULT_GENDER if None.

        Returns:
            TTSResult containing audio bytes and content_type.
        """
        target_gender = gender or self.settings.TTS_DEFAULT_GENDER
        voice_selection = resolve_voice(language=language, gender=target_gender)

        if self._override_provider is not None:
            provider = self._override_provider
        else:
            provider = get_tts_provider(
                provider_name=voice_selection.provider,
                settings=self.settings,
            )

        return await provider.synthesize(
            text=text,
            voice=voice_selection.voice,
            language=voice_selection.language,
        )
