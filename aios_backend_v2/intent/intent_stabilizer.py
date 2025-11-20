from __future__ import annotations

from typing import Any, Dict, Optional

AMBIGUOUS_PHRASES = {
    "try again",
    "again",
    "one more",
    "another one",
    "go on",
    "next",
    "keep going",
    "same again",
    "quick retry",
    "quick try again",
    "same thing",
}


def stabilize_intent(
    parsed_intent: Optional[Dict[str, Any]],
    user_message: str,
    scene_state: Optional[Dict[str, Any]] = None,
    stm_summary: Optional[str] = None,
    last_ai_action: Optional[str] = None,
) -> Dict[str, Any]:
    """Return an intent dict that is aware of scene context and STM-driven hints."""

    intent = dict(parsed_intent or {})
    text = (user_message or "").strip()
    if not text:
        return intent

    scene_type = (scene_state or {}).get("scene_type") or "none"
    scene_type = str(scene_type).lower()
    continuation_expected = bool((scene_state or {}).get("continuation_expected"))

    ambiguous = _looks_ambiguous(text)
    no_verb = not intent.get("verb")
    no_object = not intent.get("object")

    if scene_type == "game_guess" and (ambiguous or no_verb):
        return _continue_guess(intent, text, last_ai_action, stm_summary)

    if continuation_expected and (ambiguous or no_verb or no_object):
        return _continue_scene(intent, text, scene_type, last_ai_action)

    enriched = infer_missing_information(intent, scene_state, stm_summary)
    if enriched:
        intent.update(enriched)
    return intent


def infer_missing_information(
    intent: Dict[str, Any],
    scene_state: Optional[Dict[str, Any]] = None,
    stm_summary: Optional[str] = None,
) -> Dict[str, Any]:
    """Fill lightweight hints such as high-level category when parser missed it."""
    updates: Dict[str, Any] = {}
    scene_type = str((scene_state or {}).get("scene_type") or "").lower()
    obj = intent.get("object") or {}

    if not obj.get("category") and scene_type == "task":
        new_obj = dict(obj)
        new_obj["category"] = "system_task"
        if stm_summary:
            new_obj.setdefault("raw", stm_summary[:200])
        updates["object"] = new_obj

    if scene_type == "story" and not intent.get("verb"):
        updates["verb"] = "continue_story"
        new_obj = dict(obj)
        new_obj.setdefault("category", "story")
        updates["object"] = new_obj

    return updates


def _looks_ambiguous(text: str) -> bool:
    lower = text.lower()
    if lower in AMBIGUOUS_PHRASES:
        return True
    if len(lower) <= 18 and not any(ch.isdigit() for ch in lower):
        if all(word in {"ok", "okay", "sure", "please", "again", "retry"} for word in lower.split()):
            return True
    return False


def _continue_guess(
    intent: Dict[str, Any],
    user_message: str,
    last_ai_action: Optional[str],
    stm_summary: Optional[str],
) -> Dict[str, Any]:
    stabilized = dict(intent)
    stabilized["verb"] = "continue_guess"
    stabilized["channel"] = stabilized.get("channel") or "conversation"
    obj = dict(stabilized.get("object") or {})
    obj["category"] = "game_guess"
    obj["raw"] = user_message
    if stm_summary:
        obj.setdefault("context", stm_summary[:200])
    if last_ai_action:
        obj.setdefault("hint", last_ai_action)
    stabilized["object"] = obj
    stabilized["stabilized"] = True
    return stabilized


def _continue_scene(
    intent: Dict[str, Any],
    user_message: str,
    scene_type: str,
    last_ai_action: Optional[str],
) -> Dict[str, Any]:
    stabilized = dict(intent)
    stabilized["verb"] = stabilized.get("verb") or "continue_scene"
    stabilized["channel"] = stabilized.get("channel") or "conversation"
    obj = dict(stabilized.get("object") or {})
    obj["category"] = obj.get("category") or scene_type or "conversation"
    obj["raw"] = user_message
    if last_ai_action:
        obj.setdefault("hint", last_ai_action)
    stabilized["object"] = obj
    stabilized["stabilized"] = True
    return stabilized
