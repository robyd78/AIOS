from __future__ import annotations

import time
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ContextSnapshot(BaseModel):
    stm_summary: str = ""
    stm_state: Dict[str, Any] = Field(default_factory=dict)
    ltm_used: List[Dict[str, Any]] = Field(default_factory=list)
    recent_turns: List[Dict[str, str]] = Field(default_factory=list)
    scene: Dict[str, Any] = Field(default_factory=dict)
    turn_context: Dict[str, Any] = Field(default_factory=dict)
    system_prompt_excerpt: str = ""
    updated_ts: float = Field(default_factory=lambda: time.time())

    def public_view(self) -> Dict[str, Any]:
        return {
            "updated_ts": self.updated_ts,
            "stm": {
                "summary": self.stm_summary or "(none)",
                "state": self.stm_state or {},
            },
            "ltm_used": self.ltm_used,
            "recent_turns": self.recent_turns,
            "scene": self.scene,
            "turn_context": self.turn_context,
            "system_prompt_excerpt": self.system_prompt_excerpt,
        }
