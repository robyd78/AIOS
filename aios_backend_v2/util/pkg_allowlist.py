from __future__ import annotations

from typing import Dict, Optional

PACKAGE_ALLOWLIST: Dict[str, Dict[str, str]] = {
    "steam": {
        "display": "Steam",
        "apt": "steam-installer",
        "snap": "steam",
        "flatpak": "com.valvesoftware.Steam",
    },
    "onlyoffice": {
        "display": "OnlyOffice Desktop Editors",
        "apt": "onlyoffice-desktopeditors",
        "flatpak": "org.onlyoffice.desktopeditors",
    },
    "firefox": {
        "display": "Firefox",
        "apt": "firefox",
        "snap": "firefox",
        "flatpak": "org.mozilla.firefox",
    },
    "vlc": {
        "display": "VLC",
        "apt": "vlc",
        "snap": "vlc",
        "flatpak": "org.videolan.VLC",
    },
}

PACKAGE_ALIASES = {
    "steam": "steam",
    "steam-installer": "steam",
    "com.valvesoftware.steam": "steam",
    "onlyoffice": "onlyoffice",
    "only office": "onlyoffice",
    "onlyoffice-desktopeditors": "onlyoffice",
    "org.onlyoffice.desktopeditors": "onlyoffice",
    "firefox": "firefox",
    "browser": "firefox",
    "org.mozilla.firefox": "firefox",
    "vlc": "vlc",
    "org.videolan.vlc": "vlc",
}

CHANNEL_ORDER = ["apt", "snap", "flatpak"]


def resolve_package(name: str) -> Optional[str]:
    key = PACKAGE_ALIASES.get(name.lower().strip())
    if key:
        return key
    low = name.lower().strip()
    for alias, canon in PACKAGE_ALIASES.items():
        if low == alias:
            return canon
    return None


def choose_channel(canon: str, preferred: Optional[str] = None) -> Optional[str]:
    entry = PACKAGE_ALLOWLIST.get(canon)
    if not entry:
        return None
    if preferred and preferred in entry:
        return preferred
    for ch in CHANNEL_ORDER:
        if ch in entry:
            return ch
    return None


def get_package_id(canon: str, channel: str) -> Optional[str]:
    entry = PACKAGE_ALLOWLIST.get(canon)
    if not entry:
        return None
    return entry.get(channel)


def get_display_name(canon: str) -> str:
    entry = PACKAGE_ALLOWLIST.get(canon, {})
    return entry.get("display", canon.title())
