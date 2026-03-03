/**
 * Voice Agent — Frontend Application
 *
 * Handles: WebSocket connection, mic recording (push-to-talk),
 * audio playback, orb animation, and status updates.
 */

// ===== DOM Elements =====
const pttButton = document.getElementById('pttButton');
const micIcon = document.getElementById('micIcon');
const stopIcon = document.getElementById('stopIcon');
const statusText = document.getElementById('statusText');
const userTranscript = document.getElementById('userTranscript');
const userText = document.getElementById('userText');
const aiTranscript = document.getElementById('aiTranscript');
const aiText = document.getElementById('aiText');
const orbContainer = document.getElementById('orbContainer');
const waveCanvas = document.getElementById('waveCanvas');
const connectionDot = document.getElementById('connectionDot');
const connectionText = document.getElementById('connectionText');
const pttHint = document.getElementById('pttHint');

// ===== State =====
let ws = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let isProcessing = false;
let audioContext = null;
let analyser = null;
let animationFrame = null;
let disconnectedByGoodbye = false;

// ===== Particles =====
function createParticles() {
    const container = document.getElementById('particles');
    for (let i = 0; i < 30; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDuration = (8 + Math.random() * 12) + 's';
        particle.style.animationDelay = Math.random() * 10 + 's';
        particle.style.width = (1 + Math.random() * 3) + 'px';
        particle.style.height = particle.style.width;
        container.appendChild(particle);
    }
}
createParticles();

// ===== WebSocket Connection =====
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/voice`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('[WS] Connected');
        setConnectionStatus('connected');
        setStatus('Press and hold to speak');
        pttButton.classList.remove('disabled');
    };

    ws.onclose = (e) => {
        console.log('[WS] Disconnected', e.code);
        if (disconnectedByGoodbye) {
            // Don't reconnect — user said goodbye
            setConnectionStatus('goodbye');
            return;
        }
        setConnectionStatus('disconnected');
        pttButton.classList.add('disabled');
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (e) => {
        console.error('[WS] Error:', e);
        setConnectionStatus('error');
    };

    ws.onmessage = async (event) => {
        if (event.data instanceof Blob) {
            // Binary data = audio response from TTS
            await playAudio(event.data);
        } else {
            // JSON status/text message
            const msg = JSON.parse(event.data);
            handleMessage(msg);
        }
    };
}

function handleMessage(msg) {
    switch (msg.type) {
        case 'status':
            setStatus(msg.message);
            if (msg.message === 'Transcribing...') {
                setOrbState('thinking');
            } else if (msg.message === 'Thinking...') {
                setOrbState('thinking');
            } else if (msg.message === 'Speaking...') {
                setOrbState('speaking');
            } else if (msg.message === 'Ready') {
                setOrbState('idle');
                isProcessing = false;
                setStatus('Press and hold to speak');
            }
            break;

        case 'transcript':
            userTranscript.style.display = 'flex';
            userText.textContent = msg.text;
            break;

        case 'reply':
            aiTranscript.style.display = 'flex';
            aiText.textContent = msg.text;
            break;

        case 'error':
            setStatus(msg.message);
            setOrbState('idle');
            isProcessing = false;
            break;

        case 'disconnect':
            // Server is closing the connection (user said goodbye)
            console.log('[WS] Goodbye disconnect:', msg.message);
            disconnectedByGoodbye = true;
            isProcessing = true; // prevent further recording
            pttButton.classList.add('disabled');
            setStatus('👋 Session ended — goodbye!');
            pttHint.textContent = 'Refresh page to start a new chat';
            break;
    }
}

// ===== Audio Recording =====
async function startRecording() {
    if (isProcessing) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        setStatus('Not connected. Reconnecting...');
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 16000,
            }
        });

        // Set up audio visualization
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(stream);
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: getSupportedMimeType()
        });

        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                audioChunks.push(e.data);
            }
        };

        mediaRecorder.onstop = async () => {
            // Stop mic stream
            stream.getTracks().forEach(t => t.stop());

            // Stop visualization
            cancelAnimationFrame(animationFrame);
            if (audioContext) {
                audioContext.close();
                audioContext = null;
            }

            const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });

            if (audioBlob.size < 1000) {
                setStatus('Recording too short. Try again.');
                setOrbState('idle');
                isProcessing = false;
                return;
            }

            // Send audio to backend
            isProcessing = true;
            ws.send(audioBlob);
            setStatus('Processing...');
            setOrbState('thinking');
        };

        mediaRecorder.start(100); // collect every 100ms
        isRecording = true;

        // UI updates
        pttButton.classList.add('active');
        micIcon.classList.add('hidden');
        stopIcon.classList.remove('hidden');
        setOrbState('listening');
        setStatus('Listening...');
        pttHint.textContent = 'Release to send';

        // Start waveform visualization
        waveCanvas.classList.add('active');
        drawWaveform();

    } catch (err) {
        console.error('[Mic] Error:', err);
        if (err.name === 'NotAllowedError') {
            setStatus('Microphone access denied. Please allow mic access.');
        } else {
            setStatus('Microphone error: ' + err.message);
        }
    }
}

function stopRecording() {
    if (!isRecording || !mediaRecorder) return;

    mediaRecorder.stop();
    isRecording = false;

    // UI updates
    pttButton.classList.remove('active');
    micIcon.classList.remove('hidden');
    stopIcon.classList.add('hidden');
    waveCanvas.classList.remove('active');
    pttHint.textContent = 'Hold Space or click';
}

function getSupportedMimeType() {
    const types = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
    ];
    for (const type of types) {
        if (MediaRecorder.isTypeSupported(type)) {
            return type;
        }
    }
    return 'audio/webm'; // fallback
}

// ===== Audio Playback =====
async function playAudio(blob) {
    setOrbState('speaking');
    setStatus('Speaking...');

    return new Promise((resolve) => {
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);

        audio.onended = () => {
            URL.revokeObjectURL(url);
            setOrbState('idle');
            isProcessing = false;
            setStatus('Press and hold to speak');
            resolve();
        };

        audio.onerror = () => {
            URL.revokeObjectURL(url);
            setOrbState('idle');
            isProcessing = false;
            setStatus('Audio playback error');
            resolve();
        };

        audio.play().catch(err => {
            console.error('[Audio] Play error:', err);
            setOrbState('idle');
            isProcessing = false;
            resolve();
        });
    });
}

// ===== Waveform Visualization =====
function drawWaveform() {
    if (!analyser) return;

    const ctx = waveCanvas.getContext('2d');
    const width = waveCanvas.width;
    const height = waveCanvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
        animationFrame = requestAnimationFrame(draw);
        analyser.getByteFrequencyData(dataArray);

        ctx.clearRect(0, 0, width, height);

        // Draw circular waveform around the orb
        const bars = 64;
        const baseRadius = 55;
        const maxBarHeight = 30;

        for (let i = 0; i < bars; i++) {
            const angle = (i / bars) * Math.PI * 2 - Math.PI / 2;
            const dataIndex = Math.floor(i * bufferLength / bars);
            const value = dataArray[dataIndex] / 255;
            const barHeight = value * maxBarHeight;

            const x1 = centerX + Math.cos(angle) * baseRadius;
            const y1 = centerY + Math.sin(angle) * baseRadius;
            const x2 = centerX + Math.cos(angle) * (baseRadius + barHeight);
            const y2 = centerY + Math.sin(angle) * (baseRadius + barHeight);

            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.strokeStyle = `rgba(79, 143, 255, ${0.3 + value * 0.7})`;
            ctx.lineWidth = 2;
            ctx.lineCap = 'round';
            ctx.stroke();
        }
    }

    draw();
}

// ===== UI Helpers =====
function setStatus(text) {
    statusText.textContent = text;
    statusText.classList.toggle('active', text !== 'Press and hold to speak');
}

function setOrbState(state) {
    orbContainer.className = 'orb-container';
    if (state !== 'idle') {
        orbContainer.classList.add(state);
    }
}

function setConnectionStatus(status) {
    connectionDot.className = 'connection-dot';
    switch (status) {
        case 'connected':
            connectionDot.classList.add('connected');
            connectionText.textContent = 'Connected';
            break;
        case 'disconnected':
            connectionText.textContent = 'Reconnecting...';
            break;
        case 'error':
            connectionDot.classList.add('error');
            connectionText.textContent = 'Connection error';
            break;
        case 'goodbye':
            connectionDot.classList.add('error');
            connectionText.textContent = 'Disconnected — goodbye!';
            break;
    }
}

// ===== Event Listeners =====

// Mouse events
pttButton.addEventListener('mousedown', (e) => {
    e.preventDefault();
    startRecording();
});

pttButton.addEventListener('mouseup', (e) => {
    e.preventDefault();
    stopRecording();
});

pttButton.addEventListener('mouseleave', () => {
    if (isRecording) stopRecording();
});

// Touch events (mobile)
pttButton.addEventListener('touchstart', (e) => {
    e.preventDefault();
    startRecording();
});

pttButton.addEventListener('touchend', (e) => {
    e.preventDefault();
    stopRecording();
});

// Keyboard: Space to talk
document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && !e.repeat && !isRecording && !isProcessing) {
        e.preventDefault();
        startRecording();
    }
});

document.addEventListener('keyup', (e) => {
    if (e.code === 'Space' && isRecording) {
        e.preventDefault();
        stopRecording();
    }
});

// ===== Initialize =====
connectWebSocket();
