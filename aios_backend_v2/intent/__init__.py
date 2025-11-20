from __future__ import annotations

import re
from typing import Dict, Iterable, Optional, Set, Tuple

from ..util.app_resolver import expand_aliases, ALIASES as RESOLVER_ALIASES

TUI_PROGRAMS: Set[str] = {
    "htop",
    "top",
    "btop",
    "vim",
    "nano",
    "less",
    "more",
    "nmtui",
    "alsamixer",
}

TERMINAL_WORDS: Set[str] = {"terminal", "console", "shell"}
CLEAN_WORDS = {"clean", "tidy", "close", "remove"}
WORKSPACE_WORD = {"workspace", "workspaces"}

SESSION_KEYWORDS = {
    "hyprland": {"hyprland"},
    "gnome": {"gnome", "ubuntu-wayland", "ubuntu"},
}

RUN_VERBS = re.compile(r"\b(run|open|launch|start|use)\b")
FOLDER_VERBS = re.compile(r"\b(mkdir|create|make|new)\b")
FILE_VERBS = re.compile(r"\b(touch|create|make|new)\b")
PATH_PATTERN = re.compile(r"(~/\S+|/[\w\-/\.]+)")


def _find_app(text: str) -> Optional[str]:
    for alias, variants in RESOLVER_ALIASES.items():
        if alias in text:
            return variants[0]
        for variant in variants:
            if variant in text:
                return variants[0]
    return None


def _find_path(text: str) -> Optional[str]:
    match = PATH_PATTERN.search(text)
    if match:
        return match.group(1)
    return None


def infer_tool_intent(user_text: str | None, allowed_tools: Iterable[str]) -> Optional[Dict[str, object]]:
    text = (user_text or "").lower()
    if not text:
        return None
    allowed = set(allowed_tools or [])
    if not allowed:
        return None

    want_fullscreen = "fullscreen" in text.replace("-", " ") or "full screen" in text

    if "open_terminal" in allowed:
        for tui in TUI_PROGRAMS:
            if tui in text and RUN_VERBS.search(text):
                return {
                    "name": "open_terminal",
                    "arguments": {"program": tui},
                    "confidence": 0.9,
                }

    if "open_app" in allowed and RUN_VERBS.search(text):
        app_name = _find_app(text)
        if app_name:
            arguments: Dict[str, object] = {"app": app_name}
            if want_fullscreen:
                arguments["fullscreen"] = True
            return {"name": "open_app", "arguments": arguments, "confidence": 0.9}

    if "mkdir" in allowed and ("folder" in text or "directory" in text) and FOLDER_VERBS.search(text):
        path = _find_path(text)
        if path:
            return {
                "name": "mkdir",
                "arguments": {"path": path},
                "confidence": 0.85,
            }

    if "touch" in allowed and "file" in text and FILE_VERBS.search(text):
        path = _find_path(text)
        if path:
            return {
                "name": "touch",
                "arguments": {"path": path},
                "confidence": 0.85,
            }

    if "close_empty_aios_workspaces" in allowed:
        if any(word in text for word in CLEAN_WORDS) and "workspace" in text:
            return {
                "name": "close_empty_aios_workspaces",
                "arguments": {},
                "confidence": 0.8,
            }

    if "session_switch_plan" in allowed:
        for session, aliases in SESSION_KEYWORDS.items():
            if any(alias in text for alias in aliases) and ("switch" in text or "next login" in text):
                return {
                    "name": "session_switch_plan",
                    "arguments": {"target": session},
                    "confidence": 0.75,
                }

    return None
