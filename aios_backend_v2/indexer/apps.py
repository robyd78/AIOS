from __future__ import annotations

import csv
import os
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Iterable, List

from ..memory import store as memory_store

DESKTOP_DIRS = [Path("/usr/share/applications"), Path.home() / ".local/share/applications"]
TAG_KEYWORDS = {
    "office": ["office", "writer", "calc", "document"],
    "notes": ["note", "journal"],
    "browser": ["browser", "web"],
    "terminal": ["terminal", "console", "shell"],
    "media": ["music", "video", "media", "player"],
    "graphics": ["image", "photo", "draw", "paint"],
    "dev": ["developer", "ide", "code"],
}

_last_refresh_ts = 0.0


def _read_desktop_file(path: Path) -> Dict[str, str]:
    entries: Dict[str, str] = {}
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    entries[key] = value
    except Exception:
        return {}
    return entries


def _tokenize(*parts: str) -> List[str]:
    tokens: List[str] = []
    for part in parts:
        if not part:
            continue
        for token in re.split(r"[^a-zA-Z0-9]+", part.lower()):
            if token:
                tokens.append(token)
    return tokens


def _tag_entry(entry: Dict[str, str]) -> List[str]:
    tokens = _tokenize(entry.get("Name", ""), entry.get("GenericName", ""), entry.get("Comment", ""), entry.get("Categories", ""))
    entry_tags: List[str] = []
    for tag, keywords in TAG_KEYWORDS.items():
        if any(keyword in tokens for keyword in keywords):
            entry_tags.append(tag)
    return entry_tags


def _scan_desktop_entries() -> Iterable[Dict[str, object]]:
    for base in DESKTOP_DIRS:
        if not base.exists():
            continue
        for desktop_file in base.glob("*.desktop"):
            entries = _read_desktop_file(desktop_file)
            if not entries:
                continue
            yield {
                "id": desktop_file.name,
                "name": entries.get("Name"),
                "generic": entries.get("GenericName"),
                "comment": entries.get("Comment"),
                "exec": entries.get("Exec"),
                "source": "desktop",
                "categories": entries.get("Categories"),
                "tags": ",".join(_tag_entry(entries)),
                "last_seen": time.time(),
            }


def _scan_flatpak_entries() -> Iterable[Dict[str, object]]:
    if not shutil.which("flatpak"):
        return []
    out = subprocess.check_output(["flatpak", "list", "--app", "--columns=application,name"], stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) == 1:
            app_id, name = parts[0], parts[0]
        else:
            app_id, name = parts[0], parts[1]
        yield {
            "id": app_id,
            "name": name,
            "generic": None,
            "comment": None,
            "exec": f"flatpak run {app_id}",
            "source": "flatpak",
            "categories": "",
            "tags": "",
            "last_seen": time.time(),
        }


def _scan_snap_entries() -> Iterable[Dict[str, object]]:
    if not shutil.which("snap"):
        return []
    out = subprocess.check_output(["snap", "list"], stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
    lines = out.splitlines()[1:]
    for line in lines:
        if not line.strip():
            continue
        parts = line.split()
        name = parts[0]
        yield {
            "id": name,
            "name": name,
            "generic": None,
            "comment": None,
            "exec": name,
            "source": "snap",
            "categories": "",
            "tags": "",
            "last_seen": time.time(),
        }


def reindex_apps() -> None:
    entries = list(_scan_desktop_entries())
    entries.extend(_scan_flatpak_entries())
    entries.extend(_scan_snap_entries())
    if memory_store:
        memory_store.bulk_upsert_app_index(entries)


def refresh(throttle_s: int = 15, force: bool = False) -> bool:
    """Refresh the app index respecting a throttle window."""
    global _last_refresh_ts
    if memory_store is None:
        return False
    now = time.time()
    if not force and throttle_s and now - _last_refresh_ts < throttle_s:
        return False
    reindex_apps()
    _last_refresh_ts = now
    return True
