## 2025-11-08 — Dynamic Model Routing

- Router tiers (fast/mid/deep): `qwen2.5:3b-instruct`, `phi3:mini`, `llama3:8b`.
- Heuristics:
  - ≤120 chars & simple → fast
  - Tool/plan keywords or ≤600 chars → mid
  - ≥600 chars, deep keywords, or long multi-turn → deep
- Overrides:
  - Header `X-AIOS-Model` pins a specific model
  - Query `latency_ms` with <1200 forces fast tier
- Fallback ladder: deep→mid→fast with safe default if model missing
- `/chat` response now includes `{ text, model }` for telemetry

## 2025-11-08 — Dynamic Model Routing + Frontend Bindings

- Router tiers:
  - fast: qwen2.5:3b-instruct
  - mid:  phi3:mini
  - deep: llama3:8b
- Policy:
  - latency_ms < 1200 → fast
  - ≥600 chars or deep keywords or long multi-turn → deep
  - otherwise toolish/medium → mid
- Overrides: header `X-AIOS-Model`, query `latency_ms`
- Fallback ladder: deep→mid→fast, resilient if models missing
- CORS enabled for Tauri dev origins; `/health` returns `{status, ollama, piper}` with degraded state when partial
- Frontend helpers `chatOnce()` and `ttsSpeak()` provide end-to-end ask→reply→TTS flow

## Milestone: AIOS v0.1 — End-to-End Voice Chat online (LLM ↔ Backend ↔ Svelte/Tauri)

✅ Ground truth:

- Backend (FastAPI @ `127.0.0.1:8000`):
  - `/health` → `status: ok`, `ollama: true`, `piper: true`
  - `/chat` → non-stream JSON (`{ text, model }`)
  - `/tts` → WAV bytes (`Content-Type: audio/wav`)
- Ollama @ `127.0.0.1:11434`:
  - fast: `qwen2.5:3b-instruct`
  - mid: `phi3:mini`
  - deep: `llama3:8b`
- Piper voice: `~/.local/share/piper/voices/en/en_GB-northern_english_male-medium.onnx`
- Frontend:
  - Main orb input → `chatOnce(prompt, { latencyMs: 900 })` then `ttsSpeak(reply.text)`
  - Health badge in footer shows backend state + Tauri/web mode
  - Tool calls auto-executed for date/time, filesystem, shell, app launch (with permission prompts)
- CORS allowlist:
  - `http://localhost:1420`, `http://127.0.0.1:1420`, `tauri://localhost`
  - `http://localhost:5173`, `http://127.0.0.1:5173`
- Tauri v2 scaffolded (`src-tauri/`), uses `@tauri-apps/api/core` dynamic import
- Dev ergonomics:
  - `scripts/kill-ports.sh` cleans 11434 / 8000 / 1420 / 5173
  - `scripts/dev.sh` starts Ollama → Uvicorn → `npm run tauri:dev` and Ctrl-C stops all

## 2025-11-10 — Wallpaper Picker Hardening

- Wallpaper selection now uses Tauri plugins (`@tauri-apps/plugin-dialog`, `@tauri-apps/plugin-fs`) plus capability `aios.wallpaper` (dialog open + fs read).
- Frontend helper `pickWallpaper()` (see `src/lib/wallpaper.ts`) calls the plugin picker and pipes the file through `convertFileSrc()` for CSS-safe URLs.
- CSP updated (`tauri.conf.json`) to allow `img-src 'self' tauri: asset: blob: data:` so wallpapers render reliably.
- Prod view keeps wallpaper at z-index 0; orb/UI layers sit above it. Default images ship under `aios-frontend/public/wallpapers/default_#.jpg`.

## 2025-11-10 — Tool Intent Gate

- Added `aios_backend_v2/tool_gate.py`: a regex gate that inspects the latest user message and returns the subset of tools (if any) that should be visible for that turn.
- `/chat` now injects tool schemas only when the gate fires; otherwise the LLM gets a pure conversational prompt that explicitly says “No automation tools are available this turn”.
- Reduces unnecessary tool calls (e.g., greetings), keeps prompts lean, and mitigates accidental filesystem/command actions.
- `run_command_safe` / `run_command_risky` reject interactive TUIs (htop/top/less/vim/etc.) so they don’t dump control codes into the UI; the user is prompted to open a real terminal for those cases.

## 2025-11-10 — Compositor-aware Terminal Launching

- Added `aios_backend_v2/util/session.py` to detect Hyprland vs GNOME vs other compositors.
- `open_terminal` now dispatches Hyprland workspaces only when Hyprland is running; GNOME/others open terminals in-place but still report the compositor/note back to the UI.
- Tool results include a human-readable note (“Opening htop in kitty on workspace 9”), which is relayed verbatim to the frontend.
- Environment knobs: `AIOS_TERMINAL` selects kitty/foot/gnome-terminal/alacritty; `AIOS_TUI_WORKSPACE` controls the Hyprland workspace used for TUIs.

## 2025-11-10 — Workspace-aware App Launching

- `open_app` now accepts `fullscreen` (bool) and `aios_workspace` (“auto” | “none”) arguments.
- Hyprland launches: pick an unused workspace via `hyprctl workspaces -j`, switch there, tag it under `var/aios/ws/` (or `$AIOS_DATA_DIR/ws`), and optionally toggle fullscreen after launch.
- GNOME launches: stay on the current workspace but honor fullscreen when requested (per-app flags for kitty, gnome-terminal, mpv, vlc, firefox, etc.).
- Tool responses include descriptive notes (e.g., “Opening Firefox on workspace 3 (fullscreen)” vs “Opening Firefox fullscreen (current GNOME workspace)”).
- `AIOS_INTENT_V2` flag introduces a deterministic parser + gazetteer. In Phase 2 it powers tool gating + synthesis: only the relevant tool is exposed per turn, greetings keep tools hidden, and if the LLM replies with text while confidence ≥0.8 we synthesize the tool call (still respecting confirmation/one-tool-per-turn). `/debug/intent` and “what would you do?” continue to expose the parsed intent for inspection.
- Resolver stack covers Flatpak IDs, PATH binaries, and `.desktop` Exec entries; `open_app` and `resolve_app_debug` both report the source/command and surfacing install hints when an app is missing.
- `AIOS_RESOLVER_V2` enables the channel ladder (apt → snap → flatpak → AppImage). In Phase 2 it operates read-only: failures return install hints and the exact command without performing installs automatically.
- `AIOS_PKG_TOOLS` introduces advisory tools (`pkg_search`, `pkg_info`, `pkg_plan_install`). They surface install plans (apt → snap → flatpak → AppImage) and are currently read-only; the frontend renders these plans and waits for user confirmation before any future mutation.
- `AIOS_PKG_MUTATIONS_V1` extends `AIOS_PKG_TOOLS` with the allowlisted executors (`pkg_install`, `pkg_remove`, `pkg_update`). Each action runs a dry-run first, shows the exact command, and only applies after the user confirms the permission prompt.

## 2025-11-11 — Context Assembler & Telemetry

- Introduced a dedicated Context Assembler (`aios_backend_v2/context/assembler.py`). Every `/chat` turn now emits a single system prompt built from these labeled sections: `AIOS CAPABILITIES`, `CONTEXT ORIGINS` + SYSTEM NOTE, 🧠 MEMORY CONTEXT, 🖥️ SYSTEM CARD, 🎭 PERSONALITY CARD (with tone note), BEHAVIORAL POLICY/📏 GUIDELINES, base SYSTEM_PERSONA, and 🛠️ AVAILABLE TOOLS + AIOS POLICY when tools are exposed.
- Tool block now embeds an explicit policy plus compact JSON examples (`open_app`, `open_terminal`, `mkdir`). TUIs must go through `open_terminal`; ambiguous app requests trigger a clarifier instead of launching.
- Prompt structure is provenance-heavy: STM/LTM/System Card lines are fenced in YAML, with an extra “Use LTM items only if directly relevant…” reminder. Prompt dumps show the new emoji headers and the leading `SYSTEM NOTE`.
- `/chat_turns.ndjson` logs `prompt_metrics` per turn, including `stm_bytes`, `ltm_bytes`, `system_card_bytes`, `persona_bytes`, `tools_bytes`, `memory_used_flags`, `clamped` (stm/ltm/tools), and `section_order`. This makes it obvious which contexts were injected and whether any clamps occurred.
- Feature flags (`AIOS_*`) are now read via `aios_backend_v2.flag()`, keeping `.env` the single source of truth. `scripts/dev.sh` already exports `.env` before launching, so flipping flags there and restarting the backend is enough to toggle behavior.
