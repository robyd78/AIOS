from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ModelInfo:
    name: str
    tier: str  # "fast" | "mid" | "deep"


REGISTRY: Dict[str, ModelInfo] = {
    "fast": ModelInfo(os.getenv("MODEL_FAST", "qwen2.5:3b-instruct"), "fast"),
    "mid": ModelInfo(os.getenv("MODEL_MID", "phi3:mini"), "mid"),
    "deep": ModelInfo(os.getenv("MODEL_DEEP", "llama3:8b"), "deep"),
}

TOOLY = re.compile(r"\\b(plan|steps?|install|json|schema|tool|command|code|api|curl)\\b", re.I)
DEEPY = re.compile(r"\\b(analy[sz]e|compare|trade-?offs?|architecture|design|benchmark|optimi[sz]e)\\b", re.I)


def select_model(
    messages: List[Dict],
    latency_budget_ms: Optional[int] = None,
    force: Optional[str] = None,
) -> str:
    if force:
        return force

    text = " ".join(
        m.get("content", "") for m in messages[-3:] if m.get("content")
    )[:4000]
    n_chars = len(text)

    if latency_budget_ms is not None and latency_budget_ms < 1200:
        return REGISTRY["fast"].name

    if n_chars >= 600 or DEEPY.search(text) or len(messages) > 3:
        return REGISTRY["deep"].name
    if n_chars >= 120 or TOOLY.search(text):
        return REGISTRY["mid"].name

    return REGISTRY["fast"].name
