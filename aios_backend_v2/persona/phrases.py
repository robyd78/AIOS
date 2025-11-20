from __future__ import annotations

import random

PLAYFUL_REMARKS = [
    "Let's fire it up, but not literally this time.",
    "On it—no cape required.",
    "Consider it done. No extra flair, just efficiency.",
    "I'll handle it; you keep being brilliant.",
    "Is it hot in here, or am I just launching things again?",
    "Task accepted. Snark optional.",
    "Done. Still waiting for my coffee upgrade, though.",
]

DRY_REMARKS = [
    "Done. Try not to blink.",
    "Handled. No fireworks.",
    "Finished. That was thrilling, apparently.",
    "Task complete. You can exhale now.",
]


def tone_remark(tone: str | None, context: str = "general") -> str:
    tone_key = (tone or "").lower()
    if tone_key == "serious":
        return ""
    pool = PLAYFUL_REMARKS
    if tone_key == "dry":
        pool = DRY_REMARKS
    return random.choice(pool) if pool else ""
