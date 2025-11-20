from __future__ import annotations

import os
import time
from pathlib import Path

from ..settings import PROMPT_DUMP_DIR


def dump_prompt(prompt: str, enabled: bool) -> None:
    if not enabled or not prompt:
        return
    try:
        base = PROMPT_DUMP_DIR
        base.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time() * 1000)
        path = base / f"prompt_{timestamp}.txt"
        path.write_text(prompt, encoding="utf-8")
    except Exception:
        # This must never block /chat; silently swallow all errors.
        pass
