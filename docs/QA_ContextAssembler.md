# QA Checklist – Context Assembler

- **Casual chat**: Send "Hello". Verify `/chat_turns.ndjson` shows `tools_exposed: []`, STM summary mentions the greeting, and the prompt dump shows `=== RECENT CONVERSATION SUMMARY ===` with the short bullet text (no tools, no LTM facts).
- **Ambiguous app**: Ask "open office" with multiple office apps installed. Expect clarifier payload, no tool invocation until the user picks an option.
- **Clear app**: Ask "open Firefox fullscreen". Ensure exactly one tool schema is exposed; if the model responds with text, the backend synthesizes an `open_app` call (Hyprland → fullscreen workspace note, GNOME → in-place note).
- **Number game**: Run a short "Guess a number" exchange; STM should describe the game in plain language, replies must respect parity/range hints, and `chat_turns.ndjson` logs `constraint_fix:true` if a contradiction was corrected.
- **Prompt dump**: With `AIOS_DEBUG_PROMPT_DUMP=true`, inspect the latest file under `var/aios/logs/prompt_dump/` and confirm it includes `SYSTEM NOTE`, the RECENT SUMMARY block, RELEVANT LONG-TERM FACTS, scene/perona/policy sections, and the tool policy/examples when tools are available.
- **Legacy payload**: POST `{"text":"hi"}` directly to `/chat`; the backend should seed STM, record a TurnContext, and reply normally (legacy compatibility).
