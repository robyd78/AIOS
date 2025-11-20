from __future__ import annotations

import time
from typing import Any, Dict, Optional

from ..runtime import cache as runtime_cache

PERSONA_TTL_SECONDS = 300
_PERSONA_CACHE: Optional[Dict[str, Any]] = None
_PERSONA_TS: float = 0.0


def _build_user_profile(memory_store) -> Dict[str, Any]:
    profile = {"name": "Friend", "preferences": {}}
    if not memory_store:
        return profile
    stored_profile = memory_store.get_user_profile()
    name = stored_profile.get("name") or memory_store.get_pref("user_name")
    if name:
        profile["name"] = name
    prefs = {}
    for kind in ("notes_app", "office_app", "browser_app", "terminal_app"):
        val = memory_store.get_default(kind)
        if val:
            prefs[kind] = val
    if prefs:
        profile["preferences"] = prefs
    profile.update(stored_profile)
    return profile


def _build_memory_summary(memory_store, recent_turns: Optional[list] = None) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"defaults": {}, "recent_aliases": [], "recent_turns": recent_turns or []}
    if not memory_store:
        return summary
    for kind in ("notes_app", "office_app", "browser_app", "terminal_app"):
        val = memory_store.get_default(kind)
        if val:
            summary["defaults"][kind] = val
    aliases = memory_store.list_aliases(limit=5)
    summary["recent_aliases"] = [
        {"phrase": alias.get("phrase"), "target": alias.get("target"), "status": alias.get("status")}
        for alias in aliases
    ]
    return summary


def build_persona_card(user_profile: Dict[str, Any], system_card: Dict[str, Any], memory_summary: Dict[str, Any]) -> Dict[str, Any]:
    tone = (user_profile.get("tone") or memory_summary.get("tone") or "neutral").lower()
    tone_line = f"Tone selection: {tone if tone else 'neutral'} (respect user preference)."
    return {
        "identity": "AIOS Assistant",
        "role": "Voice-first desktop orchestrator for Ubuntu",
        "traits": [
            "helpful",
            "witty",
            "dry-humored",
            "empathetic but direct",
            "prefers clarity over flattery",
            "never overexplains",
        ],
        "user_profile": user_profile,
        "tone_note": tone_line,
        "session_summary": memory_summary,
        "system_snapshot": {
            "os": system_card.get("os"),
            "session": system_card.get("session"),
            "recent_apps": system_card.get("recent_launches"),
        },
        "reminders": [
            "Do not restate [STM]/[LTM]/[SC] as if the user just said them.",
            "If an LTM fact influences an answer, acknowledge softly (e.g., 'Given your saved preferences…').",
        ],
    }


def get_persona_card(system_card: Dict[str, Any], memory_store=None) -> Dict[str, Any]:
    global _PERSONA_CACHE, _PERSONA_TS
    now = time.time()
    if _PERSONA_CACHE and now - _PERSONA_TS < PERSONA_TTL_SECONDS:
        return _PERSONA_CACHE
    user_profile = _build_user_profile(memory_store)
    recent_turns = runtime_cache.get_conversation_turns()
    memory_summary = _build_memory_summary(memory_store, recent_turns)
    persona = build_persona_card(user_profile, system_card or {}, memory_summary)
    _PERSONA_CACHE = persona
    _PERSONA_TS = now
    return persona


def invalidate_persona_card() -> None:
    global _PERSONA_CACHE, _PERSONA_TS
    _PERSONA_CACHE = None
    _PERSONA_TS = 0.0
