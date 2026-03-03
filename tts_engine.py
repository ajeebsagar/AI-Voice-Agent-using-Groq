"""Text-to-Speech module using edge-tts (free Microsoft neural voices)."""

import asyncio
import io
import edge_tts

# Natural-sounding neural voice
VOICE = "en-US-AriaNeural"


async def synthesize(text: str) -> bytes:
    """
    Convert text to speech audio bytes (MP3).

    Args:
        text: The text to speak.

    Returns:
        MP3 audio bytes.
    """
    communicate = edge_tts.Communicate(text, VOICE)
    audio_buffer = io.BytesIO()

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])

    audio_bytes = audio_buffer.getvalue()
    print(f"[TTS] Synthesized {len(audio_bytes)} bytes of audio.")
    return audio_bytes


def synthesize_sync(text: str) -> bytes:
    """Synchronous wrapper for synthesize."""
    return asyncio.run(synthesize(text))
