#!/usr/bin/env bash
set -euo pipefail

PROMPT=${1:-"Summarize in two sentences why Hyprland feels snappier than GNOME."}
MODELS=("qwen2.5:3b-instruct" "phi3:mini" "llama3:8b")
RUNS=3

mkdir -p /tmp/aios-bench
echo "Prompt: $PROMPT"
echo

for M in "${MODELS[@]}"; do
  echo "== $M =="
  total=0
  last_out=""
  for i in $(seq 1 $RUNS); do
    out="/tmp/aios-bench/$(echo "$M" | tr : _).$i.out"
    last_out="$out"
    dur=$({ time -p ollama run "$M" "$PROMPT" >"$out"; } 2>&1 | awk '/^real/ {print $2}')
    echo "  run $i: ${dur}s"
    total=$(python3 - <<PY
print(${total} + float("$dur"))
PY
)
  done
  mean=$(python3 - <<PY
print(round(${total}/${RUNS}, 2))
PY
)
  head -c 220 "$last_out" | tr -d '\n'; echo -e "\n  ...\n"
  echo "  mean: ${mean}s"
  echo
done
