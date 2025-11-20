from __future__ import annotations

import glob
import os
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ALIASES: Dict[str, List[str]] = {
    "steam": ["steam", "com.valvesoftware.Steam", "steam-runtime"],
    "onlyoffice": ["onlyoffice-desktopeditors", "org.onlyoffice.desktopeditors", "only office"],
    "only office": ["onlyoffice-desktopeditors", "org.onlyoffice.desktopeditors"],
    "firefox": ["firefox", "org.mozilla.firefox"],
    "browser": ["firefox", "org.mozilla.firefox"],
    "files": ["nautilus", "org.gnome.Nautilus", "gnome-files"],
    "terminal": ["kitty", "foot", "gnome-terminal", "alacritty"],
}

FLATPAK = shutil.which("flatpak")
SNAP = shutil.which("snap")
APT = shutil.which("apt")

_CACHE: Dict[str, Tuple[float, object]] = {}
_CACHE_TTL = 90.0


def _cached(key: str, loader):
    now = time.time()
    entry = _CACHE.get(key)
    if entry and now - entry[0] < _CACHE_TTL:
        return entry[1]
    value = loader()
    _CACHE[key] = (now, value)
    return value


def expand_aliases(app: str) -> List[str]:
    appn = app.lower().strip()
    tokens = ALIASES.get(appn, [])
    if appn not in tokens:
        tokens = [appn, *tokens]
    return tokens


def _flatpak_id(name: str) -> str | None:
    if not FLATPAK:
        return None
    ids = _cached("flatpak_ids", _list_flatpak_ids)
    if name in ids:
        return name
    for fid in ids:
        if name.lower() in fid.lower():
            return fid
    return None


def _list_flatpak_ids() -> List[str]:
    if not FLATPAK:
        return []
    try:
        out = subprocess.check_output(
            ["flatpak", "list", "--app", "--columns=application"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="ignore")
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        return []


def _list_snap_apps() -> List[str]:
    if not SNAP:
        return []
    try:
        out = subprocess.check_output(["snap", "list"], stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
        lines = out.splitlines()[1:]
        return [line.split()[0] for line in lines if line.strip()]
    except Exception:
        return []


def _apt_installed(pkg: str) -> bool:
    if not APT:
        return False
    try:
        subprocess.check_output(
            ["dpkg-query", "-W", "-f=${Status}", pkg],
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _find_appimage(token: str) -> Optional[str]:
    search_dirs = [Path.home() / "Applications", Path.home()]
    for base in search_dirs:
        if not base.exists():
            continue
        for candidate in base.glob("**/*.AppImage"):
            if token.lower() in candidate.name.lower():
                return str(candidate)
    return None


def _desktop_entries() -> List[Path]:
    paths = [Path("/usr/share/applications"), Path.home() / ".local/share/applications"]
    entries: List[Path] = []
    for base in paths:
        if base.exists():
            entries.extend(base.glob("*.desktop"))
    return entries


def _parse_exec(line: str) -> List[str] | None:
    sanitized = re.sub(r"%[fFuUdDnNickvm]", "", line).strip()
    if not sanitized:
        return None
    return shlex.split(sanitized)


def _from_desktop(name: str) -> List[str] | None:
    cand = name.lower().strip()
    for entry in _desktop_entries():
        try:
            text = entry.read_text(errors="ignore")
        except Exception:
            continue
        if "exec=" not in text.lower():
            continue
        stem = entry.stem.lower()
        if cand == stem or cand in stem or cand in text.lower():
            for line in text.splitlines():
                if line.startswith("Exec="):
                    exec_line = line.split("=", 1)[1].strip()
                    argv = _parse_exec(exec_line)
                    if argv:
                        return argv
    return None


def resolve_app(app: str) -> Dict[str, object]:
    for token in expand_aliases(app):
        fid = _flatpak_id(token)
        if fid:
            return {"ok": True, "source": "flatpak", "cmd": ["flatpak", "run", fid]}

    for token in expand_aliases(app):
        exe = shutil.which(token)
        if exe:
            return {"ok": True, "source": "binary", "cmd": [token]}

    desktop_cmd = _from_desktop(app)
    if desktop_cmd:
        return {"ok": True, "source": "desktop", "cmd": desktop_cmd}

    hints = []
    lname = app.lower()
    if lname.startswith("steam"):
        hints.append("flatpak install flathub com.valvesoftware.Steam")
    if "onlyoffice" in lname or "only office" in lname:
        hints.append("flatpak install flathub org.onlyoffice.desktopeditors")
    return {"ok": False, "error": f"app '{app}' not found", "hints": hints}


def resolve_app_v2(app: str, channel_override: Optional[str] = None) -> Dict[str, object]:
    tokens: List[str] = []
    for token in expand_aliases(app):
        cleaned = token.strip()
        if cleaned and cleaned not in tokens:
            tokens.append(cleaned)
    if not tokens:
        tokens = [app]

    base_order = ["apt", "snap", "flatpak", "appimage"]
    if channel_override in base_order:
        order = [channel_override] + [c for c in base_order if c != channel_override]
    else:
        order = base_order

    snap_apps = _cached("snap_apps", _list_snap_apps)

    for channel in order:
        for token in tokens:
            if channel == "apt":
                if _apt_installed(token) or (
                    shutil.which(token) and token not in snap_apps
                ):
                    return {
                        "ok": True,
                        "channel": "apt",
                        "source": "binary",
                        "cmd": [token],
                        "package": token,
                    }
            elif channel == "snap":
                if token in snap_apps:
                    return {
                        "ok": True,
                        "channel": "snap",
                        "source": "snap",
                        "cmd": [token],
                    }
            elif channel == "flatpak":
                fid = _flatpak_id(token)
                if fid:
                    return {
                        "ok": True,
                        "channel": "flatpak",
                        "source": "flatpak",
                        "cmd": ["flatpak", "run", fid],
                    }
            elif channel == "appimage":
                path = _find_appimage(token)
                if path:
                    return {
                        "ok": True,
                        "channel": "appimage",
                        "source": "appimage",
                        "cmd": [path],
                        "warning": "AppImage launch may require execution permission.",
                    }

    desktop_cmd = _from_desktop(app)
    if desktop_cmd:
        return {
            "ok": True,
            "channel": "desktop",
            "source": "desktop",
            "cmd": desktop_cmd,
        }

    hints: List[str] = []
    primary = tokens[0]
    if channel_override in (None, "apt"):
        hints.append(f"sudo apt install {primary}")
    if channel_override in (None, "snap"):
        hints.append(f"sudo snap install {primary}")
    if channel_override in (None, "flatpak"):
        hints.append(f"flatpak install flathub {primary}")
    return {"ok": False, "error": f"app '{app}' not found", "hints": hints}
