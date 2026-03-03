"""
AI Voice Agent — FastAPI Backend

Real-time voice assistant with push-to-talk.
Pipeline: Browser Mic → WebSocket → STT → LLM → TTS → WebSocket → Browser Speaker
"""

import asyncio
import json
import os
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from stt import transcribe
from llm import chat
from tts_engine import synthesize

load_dotenv()

app = FastAPI(title="Voice Agent", version="1.0.0")

# CORS — allow all origins so the frontend can be hosted on Vercel or anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------- Routes ----------

@app.get("/")
async def index():
    """Serve the main frontend page."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "voice-agent"}


# ---------- WebSocket Voice Pipeline ----------

# Per-session conversation histories
sessions: dict[str, list[dict]] = {}

# Goodbye keywords — if the user says any of these, the session ends
GOODBYE_KEYWORDS = {"goodbye", "bye", "bye bye", "see you", "see ya", "good night",
                    "take care", "farewell", "i'm done", "that's all", "end chat",
                    "stop", "disconnect", "quit", "exit"}


def is_goodbye(text: str) -> bool:
    """Check if the transcript contains a goodbye phrase."""
    cleaned = text.lower().strip().rstrip(".!?,")
    # Exact match or the transcript contains a goodbye phrase
    if cleaned in GOODBYE_KEYWORDS:
        return True
    for keyword in GOODBYE_KEYWORDS:
        if keyword in cleaned:
            return True
    return False


@app.websocket("/ws/voice")
async def voice_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for the voice pipeline.

    Client sends: binary audio data (webm/opus)
    Server sends: JSON status messages + binary audio response (mp3)
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    sessions[session_id] = []
    print(f"[WS] Session {session_id[:8]} connected.")

    try:
        while True:
            # 1. Receive audio from client
            audio_bytes = await websocket.receive_bytes()
            print(f"[WS] Received {len(audio_bytes)} bytes of audio.")

            # Send status: transcribing
            await websocket.send_json({"type": "status", "message": "Transcribing..."})

            # 2. Speech-to-Text (runs in thread pool to not block event loop)
            loop = asyncio.get_event_loop()
            try:
                transcript = await asyncio.wait_for(
                    loop.run_in_executor(None, transcribe, audio_bytes),
                    timeout=60.0  # 60-second timeout for Render's free CPU
                )
            except asyncio.TimeoutError:
                print("[WS] STT timed out!")
                await websocket.send_json({
                    "type": "error",
                    "message": "Transcription timed out. Please try a shorter recording."
                })
                continue
            except Exception as e:
                print(f"[WS] STT error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Transcription failed. Please try again."
                })
                continue

            if not transcript:
                await websocket.send_json({
                    "type": "error",
                    "message": "Could not understand audio. Please try again."
                })
                continue

            # Send transcript to client
            await websocket.send_json({"type": "transcript", "text": transcript})

            # 3. Check for goodbye
            if is_goodbye(transcript):
                print(f"[WS] Session {session_id[:8]} — goodbye detected.")
                farewell = "Goodbye! It was nice talking to you. Take care!"

                await websocket.send_json({"type": "reply", "text": farewell})
                await websocket.send_json({"type": "status", "message": "Speaking..."})

                # Synthesize farewell audio
                audio_response = await synthesize(farewell)
                await websocket.send_bytes(audio_response)

                # Send disconnect signal — frontend will close the connection
                await websocket.send_json({"type": "disconnect", "message": "Goodbye!"})
                await websocket.close()
                sessions.pop(session_id, None)
                print(f"[WS] Session {session_id[:8]} closed (goodbye).")
                return

            # Send status: thinking
            await websocket.send_json({"type": "status", "message": "Thinking..."})

            # 4. LLM Response
            history = sessions[session_id]
            reply = await loop.run_in_executor(None, chat, transcript, history)

            # Update conversation history
            history.append({"role": "user", "content": transcript})
            history.append({"role": "assistant", "content": reply})

            # Keep history manageable (last 10 turns)
            if len(history) > 20:
                sessions[session_id] = history[-20:]

            # Send reply text to client
            await websocket.send_json({"type": "reply", "text": reply})

            # Send status: speaking
            await websocket.send_json({"type": "status", "message": "Speaking..."})

            # 5. Text-to-Speech
            audio_response = await synthesize(reply)

            # Send audio back to client
            await websocket.send_bytes(audio_response)

            # Send status: ready
            await websocket.send_json({"type": "status", "message": "Ready"})

    except WebSocketDisconnect:
        print(f"[WS] Session {session_id[:8]} disconnected.")
        sessions.pop(session_id, None)
    except Exception as e:
        print(f"[WS] Error in session {session_id[:8]}: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
        sessions.pop(session_id, None)


# ---------- Run ----------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    print(f"🎙️ Voice Agent starting on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
