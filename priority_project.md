# AIOS Context & Memory Initiative (Priority Plan)

## 1. Objective
Deliver a proven, research-backed context system so AIOS always feeds the LLM a clean, structured, and trustworthy prompt. STM, LTM, and retrieved facts must be narrated in natural language (e.g., “In past messages, the user explained…”) rather than raw logs. This is the foundation for reliable memory, clarifiers, and future teach loops.

## 2. Reference Pattern (what “good” looks like)
Industry playbooks (OpenAI cookbook, RAG/memory articles, context-engineering guides) converge on the same template:

1. System instructions + policies
2. Recent conversation summary (STM)
3. Retrieved memory facts (LTM, labeled)
4. Tool catalog / environment snapshot
5. Current user message

Memory snippets are short, curated sentences (“In a previous session…”, “Previously the user explained…”). Never dump entire transcripts; always use summaries + provenance tags.

## 3. Canonical Prompt Layout for AIOS
This is the layout we lock into `context/assembler.py` (already partially implemented, needs to remain the canonical source):

```
SYSTEM NOTE / POLICIES
AIOS CAPABILITIES
CONTEXT ORIGINS

🧠 MEMORY CONTEXT
- Goal / Latest / AIOS summary
```yaml
# [STM]
...
# [LTM]
...
# [SC]
...
```

🖥️ SYSTEM CARD
🎭 PERSONALITY CARD (with tone note)
📏 BEHAVIORAL GUIDELINES + AIOS POLICY

🛠️ AVAILABLE TOOLS (schemas + policy + JSON examples)

CURRENT USER MESSAGE
```

Key requirements:
- Every section labeled, so the LLM never confuses STM/LTM/SC with new user instructions.
- LTM block must include the reminder “Use LTM items only if directly relevant to the user’s current request.”
- Tool block must show the 3-point policy (only act when asked, clarify once, TUIs via open_terminal) plus compact JSON examples.

## 4. Memory Pipeline We’re Building
1. **STM:**
   - `seed_from_messages()` rebuilds history from incoming `messages`.
   - `_compute_summary()` outputs “Goal / Latest / AIOS” sentences (≤200 chars).
   - Clamps recorded in `prompt_metrics.clamped.stm`.

2. **LTM:**
   - Stored in `var/aios/ltm` (or `$AIOS_DATA_DIR/ltm`) with IDs, summaries, timestamps.
   - `search()` returns ≤5 hits, snippets ≤140 chars, plus the policy reminder.
   - Constraint guard merges hints from STM + latest request to keep number games consistent.

3. **Future work (post-MVP):**
   - Memory evaluator prompt per turn (decide what to store).
   - Teach loop (clarifier → alias/default write).
   - Semantic STM compression to retain assistant context more faithfully.

## 5. Anti-patterns to avoid
- Dumping raw chat logs into the prompt.
- Mixing user instructions with memory facts (no headers).
- Allowing LTM to inject unrelated side quests.
- Skipping summarization/clamping (token bloat, hallucinations).

## 6. Immediate Milestone
**Milestone: Canonical Context Template enforced everywhere.**

Checklist:
- [x] Context Assembler produces the layered template (done, untested).
- [ ] Legacy prompt builder mirrors the same sections when Context V2 flag is off.
- [x] QA checklist updated to cover STM/LTM/constraint behavior (done, untested).
- [x] Documentation (README, QA doc) references this plan (done, untested).

## 7. Next Steps After Template Lock
1. Memory evaluator prompt → decide what to store.
2. Teach/clarifier loop → capture alias/default decisions.
3. Natural-language confirmations for memory writes (no more raw JSON to the user).
4. Extract a dedicated “context router” module so `app.py` just orchestrates.
5. Tool-choice reasoning traces (hidden chain-of-thought) once the above is stable.

Keeping this doc short and living ensures everyone touches the same plan before extending STM/LTM/tooling.
