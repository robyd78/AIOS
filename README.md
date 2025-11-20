# AIOS

AIOS is a voice-first desktop orchestrator for Ubuntu. The system is split into:

- **Backend** (`aios_backend_v2/`): FastAPI app that handles intent parsing, context assembly, tool routing, Ollama LLM calls, and Piper TTS.
- **Frontend** (`aios-frontend/`): Svelte + Tauri client with orb UI, permissions modals, prompt dump, and diagnostics.
- **Dev Tooling** (`scripts/kill-ports.sh`, `scripts/dev.sh`): convenience scripts that manage Ollama, Uvicorn, and Tauri.

The rest of this doc covers architecture, feature flags, context/memory systems, tooling, telemetry, and known gaps.

---

## Architecture Overview

```
┌──────────────────────────┐      ┌───────────────────────────┐
│  aios-frontend (Tauri)   │────▶ │  /chat  (FastAPI backend) │
│  - orb UI & permissions  │◀──┐  │  - Context Assembler      │
│  - prompt dump / QA      │   │  │  - Intent + Tool Gate     │
└────────────┬─────────────┘   │  │  - Ollama / Piper bridges │
             │                 │  └───────────┬──────────────┘
             │  tools/tts       │              │
             ▼                 │              ▼
        Tool registry   ◀──────┘        System services
        (apps/fs/shell/pkg)             (Hyprland, GNOME, etc.)
```

Key backend subsystems:

1. **Context Assembler** (`aios_backend_v2/context/assembler.py`)
   - Builds a layered prompt with SYSTEM NOTE, 🧠 STM/LTM, 🖥️ System Card, 🎭 Persona, 📏 Behavioral rules, 🛠️ Tool catalog, and AIOS policy.
   - Emits `prompt_metrics` (bytes, clamps, section order) into `chat_turns.ndjson`.
2. **Memory Layers** (`memory/short_term.py`, `memory/ltm.py`)
   - STM: seeded from every incoming `messages` array; produces goal-oriented summaries.
- LTM: FAISS-backed store under `var/aios/ltm` (overridable via `AIOS_DATA_DIR`) with IDs, summaries, and policy reminders (“use only when relevant”).
3. **Intent Stack** (`lex/intent_grammar.py`, `intent/constraints.py`)
   - Deterministic verbs/actions + constraint verifier for number games.
   - Tool gate exposes only the schemas needed per turn.
4. **Tool Registry** (`tools/`) with permissions recorded in `~/.config/aios/permissions.json`.
5. **Telemetry/Logs** (`logs.py`, `var/aios/logs/`) capturing prompt metrics, cache stats, constraint fixes, clarifier options, etc.

## Requirements

- Python 3.11+
- Node 20+
- [Ollama](https://ollama.com) running locally (default `http://127.0.0.1:11434`)
- Piper CLI + voice model (`.onnx` + `.json`)

Environment variables (override if needed):

```bash
export OLLAMA_URL=http://127.0.0.1:11434
export MODEL_FAST="qwen2.5:3b-instruct"
export MODEL_MID="phi3:mini"
export MODEL_DEEP="llama3:8b"
export PIPER_MODEL=$HOME/.local/share/piper/voices/en/en_GB-northern_english_male-medium.onnx
# or export PIPER_VOICE=<path>.onnx
export AIOS_TERMINAL=kitty          # kitty|foot|gnome-terminal|alacritty for open_terminal
export AIOS_TUI_WORKSPACE=9         # default Hyprland workspace for TUIs
export AIOS_INTENT_V2=off           # enable deterministic intent parser / logging
export AIOS_RESOLVER_V2=off         # resolver v2 ladder (apt>snap>flatpak>appimage)
export AIOS_PKG_TOOLS=off           # package advisor/executor tools
export AIOS_PKG_MUTATIONS_V1=off    # enables pkg_install/pkg_remove/pkg_update (allowlist)
export AIOS_SYSTEM_CARD_V1=off      # inject SYSTEM_CARD context (OS/session facts)
export AIOS_MEMORY_DB_V1=off        # enable SQLite memory/preferences DB
export AIOS_APP_INDEX_V1=off        # desktop/flatpak/snap app indexer
export AIOS_PERSONA_V1=off          # enable persona-aware witty remarks
export AIOS_MEMORY_LTM_V1=off       # enable vector LTM store
export AIOS_CONTEXT_V2=off          # enable Context Assembler (falls back to legacy prompt when off)
export AIOS_EMBED_MODEL="e5-small-v2"
# Optional overrides (defaults now point to ./var/aios)
# export AIOS_DATA_DIR="$HOME/.local/share/aios"
export AIOS_LTM_MAX=5000
export AIOS_LTM_K=5
export AIOS_LTM_BYTES_CAP=800
```

| Flag | Purpose |
|------|---------|
| `AIOS_INTENT_V2` | Deterministic intent grammar + clarify flow + constraint verifier. |
| `AIOS_RESOLVER_V2` | Enforce resolver ladder (apt ▶ snap ▶ flatpak ▶ AppImage) with install hints. |
| `AIOS_PKG_TOOLS` / `AIOS_PKG_MUTATIONS_V1` | Read-only package advisors vs allowlisted pkg installs/removals. |
| `AIOS_SYSTEM_CARD_V1` | Inject cached OS/session/defaults/app index data at the top of the prompt. |
| `AIOS_MEMORY_DB_V1` | Enable SQLite preferences (aliases/defaults/user profile). |
| `AIOS_APP_INDEX_V1` | Desktop/Flatpak/Snap indexer + `reindex_apps` tool. |
| `AIOS_PERSONA_V1` | Persona card + tone-based remarks (playful/dry). |
| `AIOS_MEMORY_LTM_V1` | FAISS-backed LTM store + tools (`memory_ltm_*`). |
| `AIOS_CONTEXT_V2` | Toggle the structured Context Assembler (falls back to legacy prompt when off). |

All long-term memories stay local under `$AIOS_LTM_STORE`; nothing is synced externally.

Frontend dev uses `VITE_AIOS_API_BASE` (see `aios-frontend/.env`).

---

## Install

```bash
# Backend
cd ~/AIOS
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Frontend
cd ~/AIOS/aios-frontend
npm install
```

---

## Run everything

```bash
cd ~/AIOS
chmod +x scripts/kill-ports.sh scripts/dev.sh   # first time only
./scripts/kill-ports.sh    # optional cleanup
./scripts/dev.sh           # starts Ollama → Uvicorn → `npm run tauri:dev`
```

`scripts/dev.sh` traps Ctrl‑C so ports 11434 / 8000 / 1420 / 5173 are freed automatically.

Manual backend start (if needed):

```bash
source .venv/bin/activate
uvicorn aios_backend_v2.app:app --host 127.0.0.1 --port 8000
```

---

## API surface

### `GET /health`

Returns:

```json
{ "status": "ok", "ollama": true, "piper": true }
```

### `POST /chat?latency_ms=900`

Body:

```json
{ "messages": [ { "role": "user", "content": "Say hi." } ] }
```

Headers (optional):
- `X-AIOS-Model`: force `qwen2.5:3b-instruct`, `phi3:mini`, or `llama3:8b`

Response:

```json
{ "text": "Hello!", "model": "phi3:mini" }
```

### `POST /tts`

Body:

```json
{ "text": "Hello from AIOS backend." }
```

Response: WAV audio bytes (`Content-Type: audio/wav`).

---

## Tool Registry & Permissions

- `GET /tools` – catalog of available tools (name, description, JSON schemas, required permissions).
- `POST /tools/execute` – body: `{ "name": "get_datetime", "arguments": { ... } }`.  
  - Optional `override_permissions: ["perm"]` allows a one-off invocation.
  - Returns `{ "result": { ... } }`.
- `GET /tools/permissions` – current permission map.
- `POST /tools/permissions` – body `{ "permission": "apps:launch", "allow": true }` to persist consent.

Permissions are stored at `~/.config/aios/permissions.json`. Tool execution logs are appended to `var/aios/logs/tools.ndjson` (or `$AIOS_DATA_DIR/logs/tools.ndjson`).

### Tool calls from `/chat`

- LLM replies with either `{ "text": "..." }` or `{ "tool_call": { "name": "...", "arguments": { ... } } }`.
- Frontend inspects `tool_call`, optionally prompts for permissions, then invokes `/tools/execute`.
- After successful execution, the result is spoken via `ttsSpeak()`.
- Current built-in tools:
  - `get_datetime` – no permission required.
  - `open_app` – needs `apps:launch`.
  - `mkdir`, `touch` – need `fs:write`.
  - `run_command_safe` – read-only shell commands (`shell:read`).
  - `run_command_risky` – mutating shell commands (`shell:write`), always prompt before running.

---

## Frontend behavior

- Main orb input calls `chatOnce(prompt, { latencyMs: 900 })` then `ttsSpeak(text)`.
- Health badge shows `/health` status + whether we’re in Tauri or web dev mode.
- Diagnostic panel available at `?test=1` (renders REST “Chat → TTS” UI).
- Tool responses are auto-executed:
  - `get_datetime` → speaks human time.
  - `mkdir`, `touch`, `run_command_*` prompt for `fs:write`/`shell:*` permissions before mutating the filesystem.
  - `open_app` prompts for `apps:launch`. On Hyprland it can auto-pick/reuse a workspace and toggle fullscreen; on GNOME it launches fullscreen in-place when requested. With `AIOS_RESOLVER_V2=on`, resolution follows the ladder `apt → snap → flatpak → AppImage`, returning the exact command/channel and install hints instead of silently failing.
- `open_terminal` opens a real terminal window (kitty/foot/gnome-terminal/alacritty) on the configured Hyprland workspace when running Hyprland; GNOME/other compositors simply open in-place. Tool responses echo the note returned by the backend (“Opening htop in kitty on workspace 9”).
- `close_empty_aios_workspaces` (apps:launch) closes AIOS-tagged Hyprland workspaces that are currently empty.
- `session_switch_plan` (shell:read) enumerates desktop sessions and outputs safe next-login steps (LightDM `.dmrc`, GDM AccountsService hints). No forced logout occurs.
- `resolve_app_debug` (shell:read) reports which command/source `open_app` would use without launching anything—useful for diagnosing missing installs.
- `system_refresh` refreshes the cached System Card + app index snapshots; it’s read-only, respects feature flags, and is handy after you change package state outside AIOS.
- `memory_ltm_add/search/forget/prune` (behind `AIOS_MEMORY_LTM_V1`) manage the local FAISS-backed long-term store. Data never leaves `$AIOS_LTM_STORE`; the assistant only calls these when you explicitly ask (“remember that…”, “what do you remember…”, “forget memory <id>”).
- `prompt_dump` (diagnostic) prints the first 1.5KB of the active system prompt so you can inspect persona/policy text (“show your system prompt”).
- `user_profile.set` stores persona preferences (e.g., `name`, `tone`, `style`, `pref_terminal`). Phrases like “call me Lucy” or “be serious” synthesize this tool automatically.
- `logs_status` (no permissions) reports current log sizes and last rotation timestamps so you can verify rotation/perf warnings.
- With `AIOS_INTENT_V2=on`, the assistant uses a deterministic parser + confidence thresholds. High confidence → single tool_call; medium confidence → it lists the matching local apps (e.g., “OnlyOffice / LibreOffice”) and waits for you to choose; low confidence → text-only explanation.
- `pkg_search`, `pkg_info`, `pkg_plan_install` (shell:read, gated by `AIOS_PKG_TOOLS`) provide package advisor flows: list aliases, show resolver info, and present a ranked apt→snap→flatpak→AppImage install plan. No installs occur until you explicitly confirm a future pkg tool.
- `pkg_install`, `pkg_remove`, `pkg_update` (pkg:* permissions, gated by both `AIOS_PKG_TOOLS` and `AIOS_PKG_MUTATIONS_V1`) operate on a short allowlist (Steam, OnlyOffice, Firefox, VLC). Each run performs a dry-run (when supported), surfaces the exact commands, and executes only after the permission modal is confirmed. Channel preference is apt ▶ snap ▶ flatpak unless you specify e.g. “via flatpak”.
- When `AIOS_SYSTEM_CARD_V1=on`, each LLM turn receives a compact SYSTEM_CARD (OS + session + pkg managers + defaults/aliases/app snapshots) so the assistant trusts local state over general knowledge.
- Clarifier/alias loop: `/memory/alias` persists a phrase → app mapping after the user confirms; each alias starts as `provisional` and `/memory/alias/success` bumps its `success_count`, automatically promoting to `confirmed` after two successful launches. The clarifier modal now includes a “make this my default” checkbox per category—when checked, `/memory/default` stores the preference and future “open office / create a note” requests launch the chosen app automatically. Existing aliases aren’t overwritten unless you pass `force=true`, so the UI can ask for explicit confirmation before changing them.
- Debugging: when `AIOS_INTENT_V2=on`, you can inspect the deterministic parser via `GET /debug/intent?text=...` or by sending “what would you do?” after a user prompt—the assistant replies with the parsed intent JSON. These are read-only diagnostics.
- Hyprland workspaces are tagged under `var/aios/ws/`, reused when empty, and can be cleaned via `close_empty_aios_workspaces`.
- “Allow once” performs a one-off override; “Always allow” persists to `~/.config/aios/permissions.json`. Permission prompts live in `src/App.svelte` near `permissionPrompt`.
- A lightweight intent gate (`aios_backend_v2/tool_gate.py`) only exposes likely tools per turn, so chit-chat doesn’t trigger unnecessary tool calls or prompt bloat.
- Interactive TUI commands (htop/top/less/vim/etc.) are blocked in `run_command_*`; the assistant tells the user to open a terminal instead.
- Wallpaper system (prod view only):
  - Right-click → “Change wallpaper” calls `pickWallpaper()` (see `src/lib/wallpaper.ts`). Under the hood we use `@tauri-apps/plugin-dialog` to open a native picker and `convertFileSrc()` to produce a Tauri-safe URL.
  - Requires Tauri capability `aios.wallpaper` (dialog + fs read). Defaults sit in `aios-frontend/public/wallpapers/default_#.jpg`.
  - If the picker is cancelled or unavailable (e.g., web preview), we fall back to the bundled assets and log a warning. Debug the picker via DevTools console; restart Tauri if you previously denied the dialog permission.
- Test view shows the diagnostic panel (toggle prod/test via the top-right buttons).

## Context Assembler

`aios_backend_v2/context/assembler.py` constructs the system prompt for every `/chat` turn. Sections always appear in this order:

1. `### AIOS CAPABILITIES`
2. `### CONTEXT ORIGINS` + `SYSTEM NOTE`
3. 🧠 MEMORY CONTEXT (STM summary plus YAML with STM/LTM/System Card data and the LTM usage policy)
4. 🖥️ SYSTEM CARD snapshot (OS/session/pkg managers/defaults/recent apps)
5. 🎭 PERSONALITY CARD (traits, user_profile, tone note, session notes)
6. BEHAVIORAL POLICY + 📏 BEHAVIORAL GUIDELINES + base SYSTEM_PERSONA
7. 🛠️ AVAILABLE TOOLS (only when the gate exposes schemas) followed by the AIOS POLICY block

Tool block policy (rendered verbatim for the LLM):

```
TOOL POLICY:
- Call a tool only if the user asks for an action that requires it.
- If unsure which app to launch, ask one short clarifier (or use stored default).
- Never call shell TUIs via run_command_*; use open_terminal instead.
Examples:
open_app: {"tool_call":{"name":"open_app","arguments":{"app":"firefox"}}}
open_terminal: {"tool_call":{"name":"open_terminal","arguments":{"program":"htop"}}}
mkdir: {"tool_call":{"name":"mkdir","arguments":{"path":"/tmp/demo"}}}
```

### Telemetry hooks

Each chat turn logs `prompt_metrics` inside `chat_turns.ndjson`, e.g.:

```json
"prompt_metrics": {
  "stm_bytes": 128,
  "stm_tokens_est": 32,
  "ltm_count": 2,
  "ltm_bytes": 512,
  "system_card_bytes": 310,
  "persona_bytes": 900,
  "tools_bytes": 240,
  "memory_used_flags": {"stm": true, "ltm": true, "sc": true},
  "clamped": {"stm": false, "ltm": true, "tools": false},
  "section_order": ["memory","system_card","persona","tools","policy"]
}
```

STM clamps when the summary exceeds ~200 chars, LTM clamps when the YAML section hits `AIOS_LTM_BYTES_CAP`, and the tools block reports how much room the catalog + policy consumed. Use `prompt_dump` to verify the rendered sections (“SYSTEM NOTE”, emoji labels, policies, examples).

### Memory layers at a glance

- **Short-Term Memory (STM)** – `memory/short_term.py` seeds itself from each `/chat` `messages` array (`seed_from_messages`). Summaries prioritize goals, latest user line, and the most recent AIOS response. Clamp state is logged via `prompt_metrics.memory_used_flags.stm` and `clamped.stm`.
- **Long-Term Memory (LTM)** – `memory/ltm.py` stores redacted summaries + IDs under `var/aios/ltm` (configurable via `AIOS_DATA_DIR`). Searches return ≤5 hits capped at 140 chars, and the assembler prints a use-policy reminder.
- **Persona/Tone** – `persona/core.py` pulls STM snapshots, defaults, aliases, and tone preferences into a single “Tone selection …” descriptor.
- **Constraint Guard** – `intent/constraints.py` extracts numeric hints (range, parity, > / <). `chat_route` verifies LLM guesses for number games and rewrites them when contradictions appear (logged as `constraint_fix`).

### Telemetry & logs

- Runtime caches keep a short history of recent launches, Hyprland workspaces, alias hits, and clarify options. SYSTEM_CARD (when enabled) includes those recent launches so the LLM acts on live context.
- `/chat_turns.ndjson` now records intent/lookup/resolver timings, cache stats, clarify options and selections, alias/default hits, alias promotions, and whether the backend refreshed the System Card/app index. Any timing above 150 ms sets `perf_warn:true` with a reason string.
- Logs live under `var/aios/logs/`. Both `chat_turns.ndjson` and `tools.ndjson` auto-rotate at 10 MB with `.1`/`.2` backups. Oversized fields are truncated to 4 KB to keep files healthy.
- Use the `logs_status` tool to inspect current sizes and last rotation timestamps if you’re diagnosing performance or disk usage.

### Assistant policy (tools enabled)

- Trust local sources (SYSTEM_CARD, app index, aliases, defaults) over general knowledge.
- High-confidence actions → emit one `tool_call` instead of free-form instructions.
- Medium confidence (0.60–0.84) → ask one clarifying question; after the user picks, proceed with exactly one tool call.
- Low confidence (<0.60) → reply conversationally; do not run tools.
- Packages: prefer apt (deb) → snap → flatpak → AppImage, unless the user explicitly overrides (“via flatpak”), in which case note the override.
- TUIs (`htop`, `btop`, `vim`, etc.) must run via `open_terminal`; never stream curses output back through JSON.
- Mutations (installs, logouts, workspace cleanup, etc.) always require an explicit permission prompt; one tool per user message.

Examples:

```json
{"tool_call":{"name":"open_app","arguments":{"app":"firefox","fullscreen":true}}}
{"tool_call":{"name":"open_terminal","arguments":{"program":"htop"}}}
{"tool_call":{"name":"pkg_install","arguments":{"name":"steam"}}}
```

---

## Helpful docs

- `ROUTING_POLICY.md` – single source of truth for model tiers, routing, and current milestone state.
- `startup.md` – quick-start commands for daily development.
- `docs/QA_ContextAssembler.md` – smoke checklist covering prompt layering, clarifiers, and prompt_dump verification.

## Known gaps / next steps

| Area | Status |
|------|--------|
| Natural-language confirmations after memory writes | Pending – `memory_ltm_*` tools still return raw JSON (needs a conversational post-processor). |
| STM compression quality | Functional but still lossy; needs better semantic compression and clearer goal/fact separation. |
| Context router extraction | Prompt assembly lives in `context/assembler.py`, but orchestration still sits inside `app.py`. |
| Clarifier teach loop | Clarify payloads are emitted, yet alias/default persistence + UI loop remain TODO. |
| Tool reasoning traces | Deterministic gating works; richer hidden reasoning for tool choice is future work. |
