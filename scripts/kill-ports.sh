#!/usr/bin/env bash
set -euo pipefail

PORTS=(11434 8000 1420 5173)

for port in "${PORTS[@]}"; do
  echo "[kill-ports] checking ${port}"
  pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -t -i :"${port}" 2>/dev/null || true)
  else
    pids=$(ss -lptn "sport = :${port}" 2>/dev/null | awk -F',' '/pid=/{print $2}' | awk -F'=' '{print $2}' || true)
  fi
  if [ -n "${pids}" ]; then
    echo "  killing ${pids}"
    kill -9 ${pids} >/dev/null 2>&1 || true
  fi
done
