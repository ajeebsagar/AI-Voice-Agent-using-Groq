---
title: Voice Agent
emoji: 🎙️
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# 🎙️ Voice Agent

Real-time browser-based AI voice assistant with push-to-talk.

**Speak naturally and get instant voice responses** — like talking to Alexa, but fully open-source.

## Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| **Speech-to-Text** | faster-whisper (base model, CPU) | Free |
| **LLM** | Groq API (llama-3.3-70b-versatile) | Free |
| **Text-to-Speech** | edge-tts (AriaNeural voice) | Free |
| **Backend** | FastAPI + WebSocket | Free |
| **Frontend** | Vanilla HTML/CSS/JS | Free |

## Local Setup

### 1. Create & activate virtual environment

```bash
conda activate D:\All_project\ai-agents\venv
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment

Create a `.env` file:

```
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Run the server

```bash
python app.py
```

Open **http://localhost:7860** in your browser.

### 5. Usage

- **Push-to-Talk**: Hold the mic button (or Space bar) to record
- **Release** to send your voice to the AI
- **Listen** to the AI's spoken response

## Deploy to HuggingFace Spaces

1. Create a new Space with **Docker** SDK
2. Push this repo to the Space
3. Add `GROQ_API_KEY` as a secret in Space settings

## How It Works

```
Browser Mic → WebSocket → faster-whisper (STT) → Groq LLM → edge-tts (TTS) → WebSocket → Browser Speaker
```

All processing happens on the server. The browser only records audio and plays the response.
