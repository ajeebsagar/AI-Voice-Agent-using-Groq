"""Speech-to-Text module using faster-whisper (runs on CPU)."""

import io
import tempfile
import os
from faster_whisper import WhisperModel

# Use 'base' model — good accuracy, fast on CPU (~150 MB download on first run)
MODEL_SIZE = "base"

_model = None


def get_model() -> WhisperModel:
    """Lazy-load the Whisper model."""
    global _model
    if _model is None:
        print(f"[STT] Loading faster-whisper model '{MODEL_SIZE}' on CPU...")
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
        print("[STT] Model loaded successfully.")
    return _model


def transcribe(audio_bytes: bytes) -> str:
    """
    Transcribe audio bytes to text.

    Args:
        audio_bytes: Raw audio file bytes (webm, wav, mp3, etc.)

    Returns:
        Transcribed text string.
    """
    model = get_model()

    # Write audio bytes to a temp file (faster-whisper needs a file path)
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments, info = model.transcribe(tmp_path, beam_size=5, language="en")
        text = " ".join(segment.text.strip() for segment in segments)
        print(f"[STT] Transcribed: {text}")
        return text.strip()
    finally:
        os.unlink(tmp_path)
