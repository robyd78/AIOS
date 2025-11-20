from __future__ import annotations

import random
import re
from typing import Dict, Iterable, Optional

DEFAULT_STYLE = "neutral"
PLAYFUL_OPENERS = ["Alright", "Okay", "Ooooh", "Heh", "Gotcha", "Alright babe"]
WARM_OPENERS = ["Hey", "Hey friend", "Hi there", "Okay", "You got it"]
DIRECT_OPENERS = ["Sure", "Right", "Understood", "Noted"]
PLAYFUL_ENDINGS = ["😉", "😏", "🔥", "— here we go!", "— coming right up!"]
WARM_ENDINGS = ["💛", "🙂", "— happy to help!", "— you’ve got this."]
DIRECT_ENDINGS = ["", "", ".", "."]

SCENE_STYLE_OVERRIDES = {
    "game_guess": "playful",
    "task": "direct",
    "story": "warm",
}

STYLE_ALIASES = {
    "playful": "playful",
    "fun": "playful",
    "flirty": "playful",
    "humorous": "playful",
    "warm": "warm",
    "friendly": "warm",
    "supportive": "warm",
    "empathetic": "warm",
    "direct": "direct",
    "serious": "direct",
    "focus": "direct",
    "dry": "dry",
}

_STOP_PUNCTUATION = re.compile(r"[!?\.]+$")


def regulate_tone(
    text: str,
    *,
    scene_state: Optional[Dict[str, object]] = None,
    tone_pref: Optional[str] = None,
    persona_style: Optional[str] = None,
    preferences: Optional[Dict[str, object]] = None,
    persona_traits: Optional[Iterable[str]] = None,
) -> str:
    """
    Adjust assistant text to match persona+tone expectations without altering meaning.
    """
    if not text or not text.strip():
        return text

    target_style = _select_style(scene_state, tone_pref, persona_style, preferences, persona_traits)
    if target_style == DEFAULT_STYLE:
        return text

    if target_style == "playful":
        return _apply_playful(text)
    if target_style == "warm":
        return _apply_warm(text)
    if target_style == "direct":
        return _apply_direct(text)
    if target_style == "dry":
        return _apply_dry(text)
    return text


def _select_style(
    scene_state: Optional[Dict[str, object]],
    tone_pref: Optional[str],
    persona_style: Optional[str],
    preferences: Optional[Dict[str, object]],
    persona_traits: Optional[Iterable[str]],
) -> str:
    candidates = []
    if scene_state:
        scene_type = str(scene_state.get("scene_type") or "").lower()
        if scene_type in SCENE_STYLE_OVERRIDES:
            candidates.append(SCENE_STYLE_OVERRIDES[scene_type])
    if tone_pref:
        candidates.append(STYLE_ALIASES.get(tone_pref.lower(), tone_pref.lower()))
    if persona_style:
        candidates.append(STYLE_ALIASES.get(persona_style.lower(), persona_style.lower()))
    if preferences:
        pref_tone = preferences.get("tone")
        if isinstance(pref_tone, str):
            candidates.append(STYLE_ALIASES.get(pref_tone.lower(), pref_tone.lower()))
    if persona_traits:
        for trait in persona_traits:
            mapped = STYLE_ALIASES.get(str(trait).lower())
            if mapped:
                candidates.append(mapped)
    for style in candidates:
        normalized = STYLE_ALIASES.get(style, style)
        if normalized in {"playful", "warm", "direct", "dry"}:
            return normalized
    return DEFAULT_STYLE


def _ensure_prefix(text: str, candidates) -> str:
    stripped = text.lstrip()
    lower = stripped.lower()
    for candidate in candidates:
        if lower.startswith(candidate.lower()):
            return text
    prefix = random.choice(candidates)
    if not prefix.endswith(","):
        prefix = f"{prefix},"
    return f"{prefix} {stripped}"


def _ensure_suffix(text: str, endings) -> str:
    stripped = text.rstrip()
    if stripped.endswith("..."):
        return stripped
    ending = random.choice(endings)
    if not ending:
        if not _STOP_PUNCTUATION.search(stripped):
            return f"{stripped}."
        return stripped
    if ending.startswith("—") or ending.startswith(" -"):
        if stripped.endswith((".", "!", "?")):
            return f"{stripped} {ending}"
        return f"{stripped}. {ending}"
    if ending in {"😉", "😏", "🔥"}:
        if stripped.endswith((".", "!", "?")):
            return f"{stripped} {ending}"
        return f"{stripped}! {ending}"
    if not _STOP_PUNCTUATION.search(stripped):
        stripped = f"{stripped}."
    return f"{stripped} {ending}"


def _apply_playful(text: str) -> str:
    modified = _ensure_prefix(text, PLAYFUL_OPENERS)
    modified = _ensure_suffix(modified, PLAYFUL_ENDINGS)
    return modified


def _apply_warm(text: str) -> str:
    modified = _ensure_prefix(text, WARM_OPENERS)
    modified = _ensure_suffix(modified, WARM_ENDINGS)
    return modified


def _apply_direct(text: str) -> str:
    stripped = text.strip()
    if _STOP_PUNCTUATION.search(stripped):
        return stripped
    return f"{stripped}."


def _apply_dry(text: str) -> str:
    stripped = text.strip()
    if stripped.endswith("..."):
        return stripped
    if _STOP_PUNCTUATION.search(stripped):
        return stripped
    return f"{stripped}."
