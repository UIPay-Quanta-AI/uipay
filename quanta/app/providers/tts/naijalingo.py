from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from naijalingo import NaijaLingo

from app.core.config import settings as default_settings
from app.providers.tts.base import (
    TTSConfigurationError,
    TTSProvider,
    TTSProviderError,
    TTSResult,
)

if TYPE_CHECKING:
    from app.core.config import Settings


class NaijaLingoProvider(TTSProvider):
    """
    Text-to-Speech provider using the 9jaLingo SDK for Nigerian African languages:
    - Hausa (ha)
    - Igbo (ig)
    - Yoruba (yo)
    - Nigerian Pidgin (pcm)
    """

    def __init__(
        self,
        api_key: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        s = settings or default_settings
        self.api_key = api_key if api_key is not None else s.NAIJALINGO_API_KEY
        self._client: NaijaLingo | None = None

    def _get_client(self) -> NaijaLingo:
        if not self.api_key or not self.api_key.strip():
            raise TTSConfigurationError(
                "NAIJALINGO_API_KEY is missing or empty. Please set NAIJALINGO_API_KEY in environment or .env."
            )
        if self._client is None:
            try:
                self._client = NaijaLingo(api_key=self.api_key)
            except Exception as exc:
                raise TTSConfigurationError(f"Failed to initialize 9jaLingo client: {exc}") from exc
        return self._client

    async def _resolve_fallback_speaker(self, language: str, desired_voice: str) -> str | None:
        """
        Narrow speaker-not-found fallback for 9jaLingo:
        Discover speakers for language, match gender if present in desired_voice name,
        and select a compatible speaker fallback.
        """
        client = self._get_client()

        def _list_speakers():
            return client.tts.list_speakers(language=language)

        try:
            speakers = await asyncio.to_thread(_list_speakers)
            if not speakers:
                return None

            # Infer gender preference from desired_voice (e.g. 'ha' female vs male)
            desired_female = any(
                kw in desired_voice for kw in ["maryam", "obianuju", "abisoye", "dora", "female"]
            )

            for spk in speakers:
                spk_id = getattr(spk, "id", None) or getattr(spk, "speaker_id", None)
                spk_gender = getattr(spk, "gender", "").lower()
                if spk_id and spk_id != desired_voice:
                    if desired_female and spk_gender in {"female", "f"}:
                        return str(spk_id)
                    if not desired_female and spk_gender in {"male", "m"}:
                        return str(spk_id)

            # Fallback to first available speaker for language
            first_spk = next(iter(speakers), None)
            if first_spk is None:
                return None
            first_id = getattr(first_spk, "id", None) or getattr(first_spk, "speaker_id", None)
            return str(first_id) if first_id else None
        except (AttributeError, RuntimeError, ValueError, KeyError):
            return None

    async def synthesize(
        self,
        *,
        text: str,
        voice: str | None = None,
        language: str | None = None,
    ) -> TTSResult:
        """
        Synthesize speech using 9jaLingo TTS API.
        """
        if not text or not text.strip():
            raise TTSProviderError("Text cannot be empty or whitespace only.")

        if not voice:
            raise TTSProviderError(
                "Voice (speaker ID) parameter is required for 9jaLingo provider."
            )

        client = self._get_client()
        lang = language

        def _generate(target_voice: str):
            return client.tts.generate(
                text=text,
                voice=target_voice,
                lang=lang,
                response_format="wav",
            )

        try:
            response = await asyncio.to_thread(_generate, voice)
        except Exception as exc:
            exc_str = str(exc)
            # Check for 404 / speaker not found error to attempt single retry fallback
            if (
                "404" in exc_str or "speaker" in exc_str.lower() or "not found" in exc_str.lower()
            ) and lang:
                fallback_voice = await self._resolve_fallback_speaker(lang, voice)
                if fallback_voice and fallback_voice != voice:
                    try:
                        response = await asyncio.to_thread(_generate, fallback_voice)
                        voice = fallback_voice
                    except Exception as retry_exc:
                        raise TTSProviderError(
                            f"9jaLingo TTS synthesis failed with voice '{voice}' and fallback retry '{fallback_voice}': {retry_exc}"
                        ) from retry_exc
                else:
                    raise TTSProviderError(f"9jaLingo TTS synthesis failed: {exc}") from exc
            else:
                raise TTSProviderError(f"9jaLingo TTS synthesis failed: {exc}") from exc

        return TTSResult(
            audio=response.content,
            content_type=getattr(response, "media_type", "audio/wav"),
            duration_seconds=None,
            provider_metadata={
                "provider": "naijalingo",
                "voice": voice,
                "language": lang or "",
            },
        )

    async def stream(
        self,
        *,
        text: str,
        voice: str | None = None,
        language: str | None = None,
    ) -> AsyncIterator[bytes]:
        """
        Stream speech generation chunks asynchronously.
        Uses the official 9jaLingo AudioStream API.
        """
        if not text or not text.strip():
            raise TTSProviderError("Text cannot be empty or whitespace only.")

        if not voice:
            raise TTSProviderError(
                "Voice (speaker ID) parameter is required for 9jaLingo provider."
            )

        client = self._get_client()
        lang = language

        def _collect_chunks() -> list[bytes]:
            """Fully consume the sync AudioStream in a worker thread."""
            audio_stream = client.tts.stream(
                text=text,
                voice=voice,  # both voice= and speaker= work
                lang=lang,
            )

            # Preferred: use .collect() if available (returns AudioResponse)
            if hasattr(audio_stream, "collect"):
                audio = audio_stream.collect()
                content = getattr(audio, "content", None)
                if content:
                    return [content]  # single big chunk
                return []

            # Fallback: classic iteration
            chunks: list[bytes] = []
            for chunk in audio_stream:
                if chunk:
                    chunks.append(chunk)
            return chunks

        try:
            chunks = await asyncio.to_thread(_collect_chunks)
        except Exception as exc:
            raise TTSProviderError(f"9jaLingo TTS streaming failed: {exc}") from exc

        for chunk in chunks:
            yield chunk
