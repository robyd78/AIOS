from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class SceneType(str, Enum):
    NONE = "none"
    GAME_GUESS = "game_guess"
    TASK = "task"
    STORY = "story"
    CHAT = "chat"


@dataclass
class SceneState:
    scene_type: SceneType = SceneType.NONE
    last_user_intent: Optional[str] = None
    last_ai_action: Optional[str] = None
    turns_in_scene: int = 0
    continuation_expected: bool = False
    was_continuation: bool = False


_scene_state = SceneState()

GUESS_KEYWORDS = ("guess", "number", "between", "higher", "lower", "hotter", "colder")
STORY_KEYWORDS = ("story", "roleplay", "pretend", "character")
TASK_KEYWORDS = ("build", "fix", "create", "open", "install", "configure", "help me", "need to", "trying to")
GUESS_CONTINUATION_PHRASES = (
    "try again",
    "again",
    "another guess",
    "next guess",
    "close",
    "closer",
    "almost",
    "go on",
    "keep going",
    "higher",
    "lower",
    "too high",
    "too low",
    "give me another",
)
SHORT_ACK_REGEX = re.compile(r"^(?:again|sure|yep|ok|okay|yup|do it|please)$", re.IGNORECASE)


def reset_scene() -> SceneState:
    global _scene_state
    _scene_state = SceneState()
    return _scene_state


def current_scene() -> SceneState:
    return _scene_state


def scene_snapshot(state: Optional[SceneState] = None) -> Dict[str, object]:
    scene = state or _scene_state
    return {
        "scene_type": scene.scene_type.value,
        "last_user_intent": scene.last_user_intent,
        "last_ai_action": scene.last_ai_action,
        "turns_in_scene": scene.turns_in_scene,
        "continuation_expected": scene.continuation_expected,
        "was_continuation": scene.was_continuation,
    }


def detect_scene_type(message: str) -> SceneType:
    text = (message or "").strip().lower()
    if not text:
        return SceneType.NONE
    if "guess" in text or (
        any(phrase in text for phrase in ("number", "between"))
        and any(char.isdigit() for char in text)
    ):
        return SceneType.GAME_GUESS
    if any(keyword in text for keyword in STORY_KEYWORDS):
        return SceneType.STORY
    if any(keyword in text for keyword in TASK_KEYWORDS):
        return SceneType.TASK
    if "game" in text:
        return SceneType.GAME_GUESS
    return SceneType.CHAT


def is_continuation(scene: SceneState, user_message: str) -> bool:
    if scene.scene_type == SceneType.NONE:
        return False
    text = (user_message or "").strip().lower()
    if not text:
        return False
    if scene.scene_type == SceneType.GAME_GUESS:
        if any(phrase in text for phrase in GUESS_CONTINUATION_PHRASES):
            return True
        if SHORT_ACK_REGEX.match(text):
            return True
        if text.isdigit():
            return True
        if len(text.split()) <= 4 and detect_scene_type(text) == SceneType.NONE:
            return True
    else:
        detected = detect_scene_type(text)
        if detected in (SceneType.NONE, SceneType.CHAT) and (
            SHORT_ACK_REGEX.match(text) or ("?" not in text and len(text) <= 40)
        ):
            return True
    return False


def update_scene(scene: SceneState, user_message: str, ai_message: Optional[str]) -> SceneState:
    user_text = (user_message or "").strip()
    ai_text = (ai_message or "").strip()
    continuation = is_continuation(scene, user_text)
    if continuation:
        return SceneState(
            scene_type=scene.scene_type,
            last_user_intent=user_text or scene.last_user_intent,
            last_ai_action=ai_text or scene.last_ai_action,
            turns_in_scene=scene.turns_in_scene + 1,
            continuation_expected=scene.scene_type == SceneType.GAME_GUESS,
            was_continuation=True,
        )

    detected = detect_scene_type(user_text)
    if detected == SceneType.NONE:
        detected = scene.scene_type if scene.scene_type != SceneType.NONE else SceneType.CHAT if user_text else SceneType.NONE

    turns = scene.turns_in_scene + 1 if detected == scene.scene_type and scene.scene_type != SceneType.NONE else 1
    return SceneState(
        scene_type=detected,
        last_user_intent=user_text or scene.last_user_intent,
        last_ai_action=ai_text or scene.last_ai_action,
        turns_in_scene=turns if detected != SceneType.NONE else 0,
        continuation_expected=detected == SceneType.GAME_GUESS,
        was_continuation=False,
    )


def record_turn(user_message: str, ai_message: Optional[str]) -> SceneState:
    global _scene_state
    if not (user_message or ai_message):
        return _scene_state
    _scene_state = update_scene(_scene_state, user_message or "", ai_message)
    return _scene_state


def record_assistant_action(ai_message: str) -> SceneState:
    global _scene_state
    if not ai_message:
        return _scene_state
    _scene_state = SceneState(
        scene_type=_scene_state.scene_type,
        last_user_intent=_scene_state.last_user_intent,
        last_ai_action=ai_message,
        turns_in_scene=_scene_state.turns_in_scene,
        continuation_expected=_scene_state.scene_type == SceneType.GAME_GUESS,
        was_continuation=_scene_state.was_continuation,
    )
    return _scene_state


def seed_from_pairs(pairs: List[Tuple[str, str]]) -> SceneState:
    reset_scene()
    for user_text, ai_text in pairs:
        if user_text or ai_text:
            record_turn(user_text, ai_text)
    return _scene_state
