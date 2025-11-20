from __future__ import annotations

import re
from typing import Dict, Optional

from .gazetteer import canon_app_name, TUI_SET

VERBS = {
    "open": "open_app",
    "launch": "open_app",
    "start": "open_app",
    "create": "open_app",
    "run": "run",
    "execute": "run",
    "install": "pkg_install",
    "get": "pkg_install",
    "remove": "pkg_remove",
    "uninstall": "pkg_remove",
    "delete": "pkg_remove",
    "update": "pkg_update",
    "upgrade": "pkg_update",
    "search": "pkg_search",
    "find": "pkg_search",
}

CHANNELS = {"apt", "deb", "snap", "flatpak", "flathub", "appimage"}
PROFILE_TONES = {"playful", "dry", "serious"}
PROFILE_STYLES = {"concise", "detailed"}


def _find_channel(text: str) -> Optional[str]:
    for ch in CHANNELS:
        if re.search(rf"\b(via|use)\s+{re.escape(ch)}\b", text):
            if ch in {"apt", "deb"}:
                return "apt"
            if ch in {"flatpak", "flathub"}:
                return "flatpak"
            return ch
    return None


def parse_intent(text: str) -> Dict:
    raw_text = text.strip()
    t = raw_text.lower()
    verb = None
    for k, v in VERBS.items():
        if re.search(rf"\b{k}\b", t):
            verb = v
            break

    channel = _find_channel(t)
    fullscreen = bool(re.search(r"\b(fullscreen|full screen|kiosk)\b", t))
    ws_match = re.search(r"\bworkspace\s+(\d{1,2})\b", t)
    workspace = int(ws_match.group(1)) if ws_match else None
    terminal = None
    for candidate in ["kitty", "foot", "gnome-terminal", "alacritty", "terminal"]:
        if re.search(rf"\b{re.escape(candidate)}\b", t):
            terminal = candidate
            break

    obj_phrase = None
    if verb:
        m = re.search(rf"\b({'|'.join(map(re.escape, VERBS.keys()))})\b\s+(.*)", t)
        if m:
            obj_phrase = m.group(2).strip()

    obj_clean = obj_phrase or ""
    obj_clean = re.sub(r"\b(full\s*screen|fullscreen|kiosk)\b", "", obj_clean)
    obj_clean = re.sub(r"\bvia\s+\w+\b", "", obj_clean)
    obj_clean = re.sub(r"\bworkspace\s+\d+\b", "", obj_clean)
    obj_clean = obj_clean.strip()

    tui = None
    if obj_clean:
        token = obj_clean.split()[0]
        if token in TUI_SET:
            tui = token

    canon, conf = (None, 0.0)
    if obj_clean:
        canon, conf = canon_app_name(obj_clean)

    category = None
    profile_update = None
    tokens = set(obj_clean.split())
    for tag, keywords in CATEGORY_KEYWORDS.items():
        if tokens & keywords:
            category = tag
            break

    if category and tokens and all(word in CATEGORY_KEYWORDS[category] for word in tokens):
        canon, conf = (None, 0.0)

    def set_profile_update(key: str, value: str):
        nonlocal profile_update, verb
        profile_update = {"key": key, "value": value}
        verb = "profile_set"

    ltm_command = None
    if t.startswith("remember that") or t.startswith("remember this") or t.startswith("remember to"):
        payload = raw_text.split("remember", 1)[-1].replace("that", "", 1).replace("this", "", 1).strip(" .:")
        if payload:
            ltm_command = {"action": "add", "text": payload}
    elif t.startswith("save this preference") or t.startswith("save this"):
        payload = raw_text.split("save", 1)[-1].replace("this preference", "", 1).strip(" .:")
        if payload:
            ltm_command = {"action": "add", "text": payload}
    elif t.startswith("what do you remember about"):
        query = raw_text.split("about", 1)[-1].strip()
        if query:
            ltm_command = {"action": "search", "query": query}
    elif t.startswith("what do you remember"):
        query = raw_text.strip().rstrip("?.")
        if query:
            ltm_command = {"action": "search", "query": query}
    elif t.startswith("forget"):
        target = raw_text[len("forget"):].strip()
        if target:
            ltm_command = {"action": "forget", "target": target}

    for tone in PROFILE_TONES:
        if re.search(rf"(?:set (?:my )?tone (?:to|as)?\s*{tone})", t):
            set_profile_update("tone", tone)
            break
        if re.search(rf"\bbe\s+{tone}\b", t):
            set_profile_update("tone", tone)
            break

    if not profile_update:
        tone_match = re.search(r"(?:tone|mood)\s+(?:to|as)?\s*(playful|dry|serious)", t)
        if tone_match:
            set_profile_update("tone", tone_match.group(1))

    if not profile_update:
        for style in PROFILE_STYLES:
            if re.search(rf"(?:set (?:my )?style (?:to|as)?\s*{style})", t):
                set_profile_update("style", style)
                break
            if re.search(rf"\bbe\s+{style}\b", t):
                set_profile_update("style", style)
                break

    if not profile_update:
        name_match = re.search(r"\bcall me ([\w\s'-]{1,40})", raw_text, flags=re.IGNORECASE)
        if name_match:
            value = name_match.group(1).strip()
            if value:
                set_profile_update("name", value)

    return {
        "verb": verb,
        "channel": channel,
        "modifiers": {"fullscreen": fullscreen, "workspace": workspace, "terminal": terminal},
        "object": {
            "raw": obj_phrase,
            "canonical_app": canon,
            "confidence": conf,
            "tui": tui,
            "category": category,
            "profile_update": profile_update,
            "ltm_command": ltm_command,
        },
    }
CATEGORY_KEYWORDS = {
    "notes": {"note", "notes", "journal"},
    "office": {"office", "document", "writer", "calc"},
    "browser": {"browser", "web", "internet"},
    "terminal": {"terminal", "console", "shell"},
}
