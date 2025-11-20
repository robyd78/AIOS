from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Optional


class InteractionMode(str, Enum):
    CHAT = "chat"
    TASK = "task"
    GAME = "game"
    QNA = "qna"
    TOOL_RUN = "tool_run"


class ExpectedNext(str, Enum):
    ASSISTANT_REPLY = "assistant_reply"
    ASSISTANT_CONTINUE = "assistant_continue_last_action"
    USER_INPUT = "user_input_needed"
    NONE = "none"


@dataclass
class TurnContext:
    mode: InteractionMode = InteractionMode.CHAT
    expected_next: ExpectedNext = ExpectedNext.ASSISTANT_REPLY
    last_user_summary: Optional[str] = None
    last_assistant_summary: Optional[str] = None
    last_assistant_action: Optional[str] = None
    turns_in_mode: int = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "mode": self.mode.value,
            "expected_next": self.expected_next.value,
            "last_user_summary": self.last_user_summary,
            "last_assistant_summary": self.last_assistant_summary,
            "last_assistant_action": self.last_assistant_action,
            "turns_in_mode": self.turns_in_mode,
        }


QUESTION_PATTERN = re.compile(r"\?$")
ACTION_PATTERNS = (
    re.compile(r"\b(i(?:'m| am)\s+going\s+to|i(?:'m| am)\s+going\s+to)\s+", re.IGNORECASE),
    re.compile(r"\bfirst\b", re.IGNORECASE),
    re.compile(r"\bnext\b", re.IGNORECASE),
    re.compile(r"\bnow\b", re.IGNORECASE),
    re.compile(r"\b(?:i|we)\s+will\s+\b", re.IGNORECASE),
)
PLAN_PATTERNS = (
    re.compile(r"\bhelp me (?:do|build|fix|walk)\b", re.IGNORECASE),
    re.compile(r"\bstep by step\b", re.IGNORECASE),
    re.compile(r"\bwalk me through\b", re.IGNORECASE),
)
GAME_PATTERNS = (
    re.compile(r"\b(let['’]s\s+play|truth or dare|guess the)\b", re.IGNORECASE),
    re.compile(r"\b(?:game|challenge)\b", re.IGNORECASE),
)


def infer_turn_context(
    recent_messages: Iterable[Dict[str, Optional[str]]],
    stm_state: Optional[Dict[str, object]] = None,
) -> TurnContext:
    messages = [msg for msg in recent_messages if msg.get("role")]
    context = TurnContext()
    if not messages:
        return context

    last_user = _find_last(messages, "user")
    last_assistant = _find_last(messages, "assistant")

    if last_user:
        context.last_user_summary = _shorten(last_user)
        lower = last_user.lower()
        if any(p.search(lower) for p in PLAN_PATTERNS):
            context.mode = InteractionMode.TASK
        elif any(p.search(lower) for p in GAME_PATTERNS):
            context.mode = InteractionMode.GAME
        elif _looks_like_qna(messages):
            context.mode = InteractionMode.QNA

    if last_assistant:
        context.last_assistant_summary = _shorten(last_assistant)
        lower = last_assistant.lower()
        if _ends_with_question(last_assistant):
            context.expected_next = ExpectedNext.USER_INPUT
        elif any(p.search(lower) for p in ACTION_PATTERNS):
            context.expected_next = ExpectedNext.ASSISTANT_CONTINUE
        context.last_assistant_action = _infer_action_label(lower)

    if stm_state:
        goals = stm_state.get("user_goals") or []
        if isinstance(goals, list) and goals:
            context.turns_in_mode = len(goals)

    return context


def _find_last(messages: List[Dict[str, Optional[str]]], role: str) -> Optional[str]:
    for msg in reversed(messages):
        if (msg.get("role") or "").lower() == role:
            content = msg.get("content") or ""
            if content:
                return content.strip()
    return None


def _shorten(text: str, limit: int = 160) -> str:
    stripped = " ".join(text.split())
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3].rstrip() + "..."


def _ends_with_question(text: str) -> bool:
    return QUESTION_PATTERN.search(text.strip()) is not None


def _looks_like_qna(messages: List[Dict[str, Optional[str]]], window: int = 4) -> bool:
    pairs = 0
    slice_msgs = messages[-(window * 2) :]
    for idx in range(1, len(slice_msgs)):
        prev = slice_msgs[idx - 1]
        cur = slice_msgs[idx]
        if (prev.get("role") or "").lower() == "user" and (cur.get("role") or "").lower() == "assistant":
            if _ends_with_question(prev.get("content") or ""):
                pairs += 1
    return pairs >= 2


def _infer_action_label(lower_text: str) -> Optional[str]:
    if "guess" in lower_text:
        return "made_guess"
    if "asked" in lower_text or lower_text.endswith("?"):
        return "asked_question"
    if "running" in lower_text or "launching" in lower_text:
        return "ran_tool"
    if "explaining" in lower_text or "explain" in lower_text:
        return "explained_step"
    return None
