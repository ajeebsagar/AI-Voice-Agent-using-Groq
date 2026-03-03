"""Speech-to-Text module using faster-whisper (runs on CPU)."""

import tempfile
import os
import traceback
from faster_whisper import WhisperModel

# Use 'tiny' model — lightweight, works on Render free tier (~75 MB)
# Switch to 'base' for better accuracy if you have more RAM
MODEL_SIZE = os.getenv("WHISPER_MODEL", "tiny")

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
        Transcribed text string, or empty string on failure.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        print("[STT] Audio too short, skipping.")
        return ""

    model = get_model()

    # Write audio bytes to a temp file (faster-whisper needs a file path)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        segments, info = model.transcribe(
            tmp_path,
            beam_size=1,       # faster, less memory
            language="en",
            vad_filter=True,   # skip silence for speed
        )
        text = " ".join(segment.text.strip() for segment in segments)
        print(f"[STT] Transcribed ({info.duration:.1f}s audio): {text}")
        return text.strip()

    except Exception as e:
        print(f"[STT] Error during transcription: {e}")
        traceback.print_exc()
        return ""

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass
