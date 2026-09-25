from __future__ import annotations

import edge_tts

from app.providers.tts.base import TTSProvider, TTSProviderError, TTSResult

EDGE_VOICES = {
    "female": "en-NG-EzinneNeural",
    "male": "en-NG-AbeoNeural",
}


class EdgeTTSProvider(TTSProvider):
    """
    Text-to-Speech provider using edge-tts (Microsoft Edge Online TTS).

    Supports Nigerian English voices:
    - Female: en-NG-EzinneNeural
    - Male: en-NG-AbeoNeural
    """

    def __init__(
        self,
        default_voice: str = "en-NG-EzinneNeural",
        default_language: str = "en-NG",
    ) -> None:
        self.default_voice = default_voice
        self.default_language = default_language

    async def synthesize(
        self,
        *,
        text: str,
        voice: str | None = None,
        language: str | None = None,
    ) -> TTSResult:
        """
        Synthesize text using edge-tts.
        """
        if not text or not text.strip():
            raise TTSProviderError("Text cannot be empty or whitespace only.")

        v = voice or self.default_voice
        l = language or self.default_language

        try:
            communicate = edge_tts.Communicate(text=text, voice=v)
            audio_bytes = b""
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    audio_bytes += chunk.get("data", b"")

            if not audio_bytes:
                raise TTSProviderError("Edge TTS produced empty audio response.")

            return TTSResult(
                audio=audio_bytes,
                content_type="audio/mpeg",
                duration_seconds=None,
                provider_metadata={
                    "provider": "edge",
                    "voice": v,
                    "language": l,
                },
            )
        except TTSProviderError:
            raise
        except Exception as exc:
            raise TTSProviderError(f"Edge TTS synthesis failed: {exc}") from exc
