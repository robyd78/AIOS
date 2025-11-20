from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
from typing import Dict, List, Set, Tuple


GAZETTEER: Dict[str, List[str]] = {
    "onlyoffice-desktopeditors": [
        "onlyoffice",
        "only office",
        "org.onlyoffice.desktopeditors",
        "onlyoffice-desktopeditors",
        "onlyoffice editors",
    ],
    "steam": ["steam", "com.valvesoftware.Steam", "steam runtime"],
    "firefox": ["firefox", "org.mozilla.firefox", "browser"],
    "nautilus": [
        "files",
        "file manager",
        "nautilus",
        "org.gnome.Nautilus",
        "gnome files",
    ],
    "kitty": ["kitty", "terminal", "console"],
    "gnome-terminal": ["gnome terminal", "gnome-terminal"],
    "alacritty": ["alacritty"],
    "foot": ["foot"],
}

TUI_SET: Set[str] = {
    "htop",
    "btop",
    "top",
    "vim",
    "nano",
    "less",
    "more",
    "nmtui",
    "alsamixer",
    "mc",
}


def canon_app_name(user_text: str) -> Tuple[str | None, float]:
    """Fuzzy map the provided app label to our canonical gazetteer key."""

    s = user_text.strip().lower()
    if not s:
        return None, 0.0

    for canon, aliases in GAZETTEER.items():
        alias_set = [a.lower() for a in aliases]
        if s == canon or s in alias_set:
            return canon, 1.0

    alias_map = {alias.lower(): canon for canon, aliases in GAZETTEER.items() for alias in [canon, *aliases]}
    candidates = list(alias_map.keys())
    match = get_close_matches(s, candidates, n=1, cutoff=0.72)
    if match:
        return alias_map[match[0]], 0.8
    return None, 0.0


def expand_aliases(canonical: str) -> List[str]:
    return [canonical, *GAZETTEER.get(canonical, [])]

