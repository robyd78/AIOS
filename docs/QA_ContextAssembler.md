# QA Checklist – Context Assembler

- **Casual chat**: Send "Hello". Verify `/chat_turns.ndjson` shows `tools_exposed: []`, STM contains the last user line, and the MEMORY CONTEXT block still lists `(none)` or the current LTM hits if enabled.
- **Ambiguous app**: Ask "open office" with multiple office apps installed. Expect clarifier payload, no tool invocation until the user picks an option.
- **Clear app**: Ask "open Firefox fullscreen". Ensure exactly one tool schema is exposed; if the model responds with text, the backend synthesizes an `open_app` call (Hyprland → fullscreen workspace note, GNOME → in-place note).
- **Number game**: Run a short "Guess a number" exchange; STM should describe the current game state, replies must respect parity/range hints, and `chat_turns.ndjson` logs `constraint_fix:true` if a contradiction was corrected.
- **Prompt dump**: Trigger `prompt_dump` (“show your system prompt”) and confirm the output includes `SYSTEM NOTE`, emoji-labeled MEMORY/SYSTEM/PERSONA blocks, and the tool policy/examples when tools are available.
- **Legacy payload**: POST `{"text":"hi"}` directly to `/chat`; the backend should seed STM and reply normally (legacy compatibility).
