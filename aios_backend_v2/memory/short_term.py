from __future__ import annotations

import collections
import re
from dataclasses import asdict, dataclass, field
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from ..state import scene_manager


@dataclass
class STMSummary:
    text: str = ""
    tokens_est: int = 0


_MAX_TURNS = 6
_history: Deque[Tuple[str, str]] = collections.deque(maxlen=_MAX_TURNS)
_summary: str = ""
_clamped: bool = False
_last_state: Optional["STMState"] = None
_last_summary = STMSummary()
_MAX_SUMMARY_CHARS = 600
_MAX_LIST_ITEMS = 3
_GOAL_RE = re.compile(
    r"\b(open|install|run|launch|remember|note|create|guess|search|find|build|fix|write|explain|want|need|trying)\b",
    re.IGNORECASE,
)
_QUESTION_RE = re.compile(r"\?$")
_GOAL_PATTERNS = [
    re.compile(r"(?:i\s*(?:want|need|plan|hope)\s*to)\s+(?P<goal>[^.?!]+)", re.IGNORECASE),
    re.compile(r"(?:my\s+goal\s+is|goal:)\s*(?P<goal>[^.?!]+)", re.IGNORECASE),
    re.compile(r"(?:help\s+me\s+)?(?:remember|figure out)\s+(?P<goal>[^.?!]+)", re.IGNORECASE),
]
_META_PREFIXES = (
    r"^(?:remember|please remember|let['’]?s)\s*[:\-,\s]+",
    r"^(?:hey|hi)[,!\s]+",
)


def reset(history: List[Dict[str, str]]) -> str:
    _history.clear()
    pairs: List[Tuple[str, str]] = []
    for turn in history[-_MAX_TURNS:]:
        user = turn.get("user", "")
        assistant = turn.get("assistant", "")
        if user or assistant:
            pairs.append((user, assistant))
    for user, assistant in pairs:
        _history.append((user, assistant))
    scene_manager.seed_from_pairs(list(_history))
    return _compute_summary()


def update(history: List[Dict[str, str]]) -> str:
    for turn in history[-_MAX_TURNS:]:
        user = turn.get("user", "")
        assistant = turn.get("assistant", "")
        if user or assistant:
            _history.append((user, assistant))
            scene_manager.record_turn(user, assistant)
    return _compute_summary()


def push(user_text: str, assistant_text: str) -> str:
    if not (user_text or assistant_text):
        return _summary
    updated_existing = False
    if _history:
        last_user, last_ai = _history[-1]
        if last_user == user_text and not last_ai:
            _history[-1] = (user_text, assistant_text)
            scene_manager.record_assistant_action(assistant_text or "")
            updated_existing = True
    if not updated_existing:
        _history.append((user_text, assistant_text))
        scene_manager.record_turn(user_text, assistant_text)
    return _compute_summary()


def seed_from_messages(messages: List[Dict[str, str]] | List[object]) -> str:
    """Rebuild history from raw chat messages (user/assistant pairs)."""
    if not messages:
        return _summary
    trimmed = _pairs_from_messages(messages)
    if not trimmed:
        return _summary
    _history.clear()
    for user_text, assistant_text in trimmed:
        _history.append((user_text, assistant_text))
    scene_manager.seed_from_pairs(list(_history))

    return _compute_summary()


def _pairs_from_messages(messages: List[Dict[str, str]] | List[object]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    pending_user: Optional[str] = None
    for msg in messages:
        role: Optional[str]
        content = ""
        if isinstance(msg, dict):
            role = msg.get("role")
            content = (msg.get("content") or "").strip()
        else:
            role = getattr(msg, "role", None)
            content = (getattr(msg, "content", None) or "").strip()
        if not role:
            continue
        role = role.lower()
        if role == "user":
            pending_user = content
        elif role == "assistant":
            user_text = pending_user if pending_user is not None else ""
            pairs.append((user_text, content))
            pending_user = None
    if pending_user is not None:
        pairs.append((pending_user, ""))
    return pairs[-_MAX_TURNS:]


def build_stm_summary(messages: List[Dict[str, str]] | List[object]) -> STMSummary:
    pairs = _pairs_from_messages(messages)
    if not pairs:
        return STMSummary()
    state = _build_state(pairs)
    summary = _compose_summary_text(state)
    return _finalize_summary(summary)


def _prepare_pairs(pairs: Optional[Iterable[Tuple[str, str]]] = None) -> List[Tuple[str, str]]:
    if pairs is None:
        return list(_history)
    return list(pairs)


def _normalize(text: str, limit: int = 160) -> str:
    cleaned = " ".join((text or "").strip().split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _smart_trim(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    cut = text.rfind(". ", 0, limit)
    if cut == -1:
        cut = text.rfind(" ", 0, limit)
    if cut == -1:
        cut = limit
    return text[:cut].rstrip(" .") + "..."


def _recent_user_messages(
    history: Optional[Iterable[Tuple[str, str]]] = None, limit: int = _MAX_LIST_ITEMS
) -> List[str]:
    collected: List[str] = []
    for user, _ in reversed(_prepare_pairs(history)):
        norm = _normalize(_strip_meta(user))
        if norm:
            collected.append(norm)
        if len(collected) >= limit:
            break
    return collected


def _recent_assistant_messages(
    history: Optional[Iterable[Tuple[str, str]]] = None, limit: int = _MAX_LIST_ITEMS
) -> List[str]:
    collected: List[str] = []
    for _, assistant in reversed(_prepare_pairs(history)):
        norm = _normalize(assistant)
        if norm:
            collected.append(norm)
        if len(collected) >= limit:
            break
    return collected


def _extract_goals(
    history: Optional[Iterable[Tuple[str, str]]] = None, limit: int = _MAX_LIST_ITEMS
) -> List[str]:
    goals: List[str] = []
    for user, _ in reversed(_prepare_pairs(history)):
        norm = _normalize(_strip_meta(user))
        if norm and _GOAL_RE.search(norm):
            phrase = _goal_phrase(norm)
            if phrase and phrase not in goals:
                goals.append(phrase)
        if len(goals) >= limit:
            break
    return goals


def _extract_questions(
    history: Optional[Iterable[Tuple[str, str]]] = None, limit: int = _MAX_LIST_ITEMS
) -> List[str]:
    questions: List[str] = []
    seen: set[str] = set()
    for user, _ in reversed(_prepare_pairs(history)):
        norm = _normalize(_strip_meta(user))
        if norm and ("?" in norm or _QUESTION_RE.search(norm)):
            question = norm.rstrip(". ")
            if question not in seen:
                questions.append(question)
                seen.add(question)
        if len(questions) >= limit:
            break
    return questions


def _compute_summary() -> str:
    global _summary, _clamped, _last_state, _last_summary
    state = _build_state()
    _last_state = state
    summary_obj = _compose_summary_text(state)
    summary_obj = _finalize_summary(summary_obj)
    _clamped = len(summary_obj.text) >= _MAX_SUMMARY_CHARS
    _summary = summary_obj.text
    _last_summary = summary_obj
    return summary_obj.text


def _build_state(pairs: Optional[Iterable[Tuple[str, str]]] = None) -> STMState:
    user_msgs = _recent_user_messages(pairs)
    assistant_msgs = _recent_assistant_messages(pairs)
    goals = _extract_goals(pairs)
    questions = _extract_questions(pairs)

    state = STMState()
    state.current_topic = _derive_topic(user_msgs, assistant_msgs)
    state.user_goals = goals[:_MAX_LIST_ITEMS]
    state.last_actions = assistant_msgs[:_MAX_LIST_ITEMS] if assistant_msgs else []
    state.open_questions = questions[:_MAX_LIST_ITEMS]
    return state


def _compose_summary_text(state: STMState) -> STMSummary:
    lines: List[str] = ["Recent conversation summary:"]
    topic = state.current_topic or "General conversation about the user's desktop tasks."
    lines.append(f"- Topic: {topic}")

    if state.user_goals:
        lines.append(f"- User goal: {_join_phrases(state.user_goals)}")
    else:
        lines.append("- User goal: Not explicitly stated; continuing general chat.")

    if state.last_actions:
        lines.append(f"- Assistant has: {_join_phrases(state.last_actions)}")
    else:
        lines.append("- Assistant has: acknowledged but not acted yet.")

    if state.open_questions:
        lines.append(f"- Open: {_join_phrases(state.open_questions)}")

    text = "\n".join(lines).strip()
    tokens_est = len(text.encode("utf-8")) // 4 if text else 0
    return STMSummary(text=text, tokens_est=tokens_est)


def get_summary(debug: bool = False):
    if debug:
        return {
            "summary": _last_summary.text,
            "tokens_est": _last_summary.tokens_est,
            "turns": list(_history),
            "clamped": _clamped,
            "scene": scene_manager.scene_snapshot(),
            "state": get_state_dict(),
        }
    return _last_summary.text


def get_summary_obj() -> STMSummary:
    return _last_summary


def get_scene_snapshot() -> Dict[str, object]:
    return scene_manager.scene_snapshot()


def _goal_phrase(text: str) -> str:
    for pattern in _GOAL_PATTERNS:
        match = pattern.search(text)
        if match:
            goal = match.group("goal").strip(" .")
            if goal:
                return goal
    return text


def _strip_meta(text: str) -> str:
    stripped = text or ""
    for pattern in _META_PREFIXES:
        stripped = re.sub(pattern, "", stripped, flags=re.IGNORECASE)
    return stripped.strip()


def _derive_topic(user_msgs: List[str], assistant_msgs: List[str]) -> Optional[str]:
    if user_msgs:
        topic = user_msgs[0]
        if len(topic) < 4 and assistant_msgs:
            return f"Assistant recently said: {assistant_msgs[0]}"
        return topic
    if assistant_msgs:
        return f"Assistant recently said: {assistant_msgs[0]}"
    return None


@dataclass
class STMState:
    current_topic: Optional[str] = None
    user_goals: List[str] = field(default_factory=list)
    last_actions: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)


def get_state_dict() -> Dict[str, List[str] | Optional[str]]:
    if _last_state is None:
        return {}
    return asdict(_last_state)


def _join_phrases(items: List[str], limit: int = 2) -> str:
    if not items:
        return ""
    trimmed = items[:limit]
    if len(items) > limit:
        trimmed.append("...")
    return "; ".join(trimmed)


def _finalize_summary(summary: STMSummary) -> STMSummary:
    text = summary.text.strip()
    if len(text) > _MAX_SUMMARY_CHARS:
        text = text[: _MAX_SUMMARY_CHARS - 3].rstrip() + "..."
    tokens_est = len(text.encode("utf-8")) // 4 if text else 0
    return STMSummary(text=text, tokens_est=tokens_est)
