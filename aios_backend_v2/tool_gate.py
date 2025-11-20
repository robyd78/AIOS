"""Heuristics for deciding which tools to expose to the LLM."""

from __future__ import annotations

import re
from typing import Iterable, Optional, Set, Tuple

from .intent import TERMINAL_WORDS, TUI_PROGRAMS, infer_tool_intent
from .util.app_resolver import ALIASES as RESOLVER_ALIASES

APP_HINTS = set(RESOLVER_ALIASES.keys())
_META_LINE_PATTERNS = (
    re.compile(r"^### "),
    re.compile(r"^```"),
    re.compile(r"^\s*(?:stm:|ltm:|system_card:)"),
    re.compile(r"^\s*(?:-{0,2}\s*)?(?:id:|kind:|ts:|text:|count:|summary:|tokens:)"),
)


def _has(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text))


def _strip_meta_lines(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        if any(pattern.match(line) for pattern in _META_LINE_PATTERNS):
            continue
        lines.append(line)
    return "\n".join(lines)


def analyze_request(
    latest_user_text: str | None, available_tools: Iterable[str]
) -> Tuple[Set[str], Optional[dict]]:
    """Return (tools, intent) for the given user text."""

    cleaned = _strip_meta_lines(latest_user_text or "")
    text = cleaned.lower()
    if not text:
        return set(), None

    available = set(available_tools or [])
    picks: Set[str] = set()

    def allow(name: str) -> None:
        if name in available:
            picks.add(name)

    mentions_terminal = any(word in text for word in TERMINAL_WORDS)
    tui_present = any(word in text for word in TUI_PROGRAMS)
    has_command_verb = _has(r"\b(run|open|launch|start|use)\b", text)

    interactive_requested = False
    if tui_present and (has_command_verb or text.strip() in TUI_PROGRAMS):
        interactive_requested = True
    if mentions_terminal and _has(r"\b(open|launch|start)\b", text):
        interactive_requested = True

    if _has(r"\b(time|date|day|today|tonight|morning)\b", text):
        allow("get_datetime")

    allow_open_app = not interactive_requested and (
        _has(r"\b(open|launch|start)\b", text) or any(hint in text for hint in APP_HINTS)
    )
    if allow_open_app:
        allow("open_app")

    if _has(r"\b(mkdir|create (?:a )?folder|new directory|make directory)\b", text):
        allow("mkdir")

    if _has(r"\b(touch|create (?:a )?file|new file|make file)\b", text):
        allow("touch")

    if interactive_requested:
        allow("open_terminal")
    else:
        if _has(r"\b(run|execute|show|list|display)\b", text) or _has(r"\b(ls|cat|ps)\b", text):
            allow("run_command_safe")

    if _has(r"\b(remove|rm|delete|wipe|install)\b", text):
        allow("run_command_risky")

    if "close_empty_aios_workspaces" in available and "workspace" in text:
        if any(word in text for word in ("clean", "tidy", "close", "remove")):
            allow("close_empty_aios_workspaces")

    if "session_switch_plan" in available and "switch" in text:
        allow("session_switch_plan")

    intent = infer_tool_intent(text, picks)
    return picks, intent


def gate_tools(latest_user_text: str | None, available_tools: Iterable[str]) -> Set[str]:
    tools, _ = analyze_request(latest_user_text, available_tools)
    return tools
