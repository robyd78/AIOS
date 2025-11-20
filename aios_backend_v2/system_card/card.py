from __future__ import annotations

import functools
import os
import platform
import shutil
import subprocess
import time
from typing import Dict, List

from ..memory import store as memory_store
from ..runtime import cache as runtime_cache

CACHE_TTL = 60.0
_last_card: Dict[str, object] | None = None
_last_ts: float = 0.0


def _run(cmd: List[str]) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def _detect_os() -> Dict[str, str]:
    return {
        "name": _run(["lsb_release", "-ds"]) or platform.platform(),
        "kernel": platform.release(),
        "arch": platform.machine(),
    }


def _detect_session() -> Dict[str, str]:
    compositor = "other"
    if os.getenv("HYPRLAND_INSTANCE_SIGNATURE"):
        compositor = "hyprland"
    else:
        desk = (os.getenv("XDG_CURRENT_DESKTOP") or "").lower()
        sess = (os.getenv("DESKTOP_SESSION") or "").lower()
        if "gnome" in desk or "gnome" in sess:
            compositor = "gnome"
    dm = "unknown"
    for candidate in ("gdm", "lightdm", "sddm"):
        if shutil.which(candidate):
            dm = candidate
            break
    display = "wayland" if (os.getenv("WAYLAND_DISPLAY")) else "x11"
    return {"compositor": compositor, "display_manager": dm, "display": display}


def _detect_pkg_managers() -> Dict[str, bool]:
    return {
        "apt": shutil.which("apt") is not None,
        "snap": shutil.which("snap") is not None,
        "flatpak": shutil.which("flatpak") is not None,
    }


def _collect_defaults() -> Dict[str, str]:
    defaults = {}
    kinds = ("notes_app", "office_app", "browser_app", "terminal_app", "tui_workspace")
    for kind in kinds:
        val = memory_store.get_default(kind) if memory_store else None
        if val:
            defaults[kind] = val
    return defaults


def _collect_aliases(limit: int = 10) -> List[Dict[str, object]]:
    if not memory_store:
        return []
    return memory_store.list_aliases(limit)


def _collect_apps_by_tag(tag: str, limit: int = 2) -> List[Dict[str, object]]:
    if not memory_store:
        return []
    return memory_store.search_app_index_by_tag(tag, limit)


def get_system_card() -> Dict[str, object]:
    global _last_card, _last_ts
    now = time.time()
    if _last_card and now - _last_ts < CACHE_TTL:
        return _last_card
    card = {
        "os": _detect_os(),
        "session": _detect_session(),
        "pkg_managers": _detect_pkg_managers(),
        "defaults": _collect_defaults(),
        "aliases": _collect_aliases(),
        "recent_launches": runtime_cache.get_recent_launches(),
        "apps": {
            "notes": _collect_apps_by_tag("notes", 2),
            "office": _collect_apps_by_tag("office", 2),
            "browser": _collect_apps_by_tag("browser", 1),
            "terminal": _collect_apps_by_tag("terminal", 1),
        },
    }
    _last_card = card
    _last_ts = now
    return card


def invalidate_cache() -> None:
    global _last_card, _last_ts
    _last_card = None
    _last_ts = 0.0
