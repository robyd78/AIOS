# Startup Guide

1. **Prep environment**
   ```bash
   cd ~/AIOS
   ./scripts/kill-ports.sh        # optional cleanup
   ```

2. **Run everything**
   ```bash
   ./scripts/dev.sh
   ```
   - Starts Ollama (127.0.0.1:11434) if not already running
   - Launches FastAPI backend (uvicorn on 127.0.0.1:8000)
   - Runs `npm run tauri:dev` to open the desktop window
   - Ctrl‑C stops all child processes

3. **Manual checks (optional)**
   ```bash
   source .venv/bin/activate
   curl -s http://127.0.0.1:8000/health | jq
   curl -s -X POST 'http://127.0.0.1:8000/chat?latency_ms=900' \
     -H 'Content-Type: application/json' \
     -d '{"messages":[{"role":"user","content":"Say hi in one sentence."}]}'
   curl -s -X POST http://127.0.0.1:8000/tts \
     -H 'Content-Type: application/json' \
     -d '{"text":"Hello from AIOS backend."}' -o /tmp/test.wav && aplay /tmp/test.wav
   ```
