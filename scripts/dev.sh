#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  echo
  echo "[dev] stopping all services"
  pkill -P $$ >/dev/null 2>&1 || true
}
trap cleanup INT TERM EXIT

if ! ss -ltn | grep -q ':11434'; then
  echo "[dev] starting ollama serve"
  (ollama serve >/tmp/ollama.dev.log 2>&1 &) 
  sleep 1
fi

echo "[dev] starting backend on :8000"
(
  cd "$ROOT"
  if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
set -a; [ -f .env ] && . ./.env; set +a
  fi
  export OLLAMA_URL=${OLLAMA_URL:-http://127.0.0.1:11434}
  export PIPER_MODEL=${PIPER_MODEL:-$HOME/.local/share/piper/voices/en/en_GB-northern_english_male-medium.onnx}
  uvicorn aios_backend_v2.app:app --host 127.0.0.1 --port 8000
) &

sleep 1

echo "[dev] starting tauri dev"
(
  cd "$ROOT/aios-frontend"
  npm run tauri:dev
) &

wait
