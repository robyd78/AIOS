from __future__ import annotations

from typing import Dict, List, Optional

from .app_resolver import (
    expand_aliases,
    _apt_installed,
    _flatpak_id,
    _find_appimage,
    _list_snap_apps,
    _cached,
    APT,
    SNAP,
    FLATPAK,
)


def build_install_plan(app: str, channel_override: Optional[str] = None) -> List[Dict[str, object]]:
    tokens = expand_aliases(app)
    if not tokens:
        tokens = [app]
    snap_apps = set(_cached("snap_apps", _list_snap_apps))
    plan: List[Dict[str, object]] = []

    def add_step(channel: str, cmd: str, reason: str, available: bool) -> None:
        plan.append(
            {
                "channel": channel,
                "cmd": cmd,
                "reason": reason,
                "available": available,
            }
        )

    order = ["apt", "snap", "flatpak", "appimage"]
    if channel_override in order:
        order.remove(channel_override)
        order.insert(0, channel_override)

    for channel in order:
        token = tokens[0]
        if channel == "apt":
            available = bool(APT)
            state = "already installed" if _apt_installed(token) else "install"
            add_step("apt", f"sudo apt install {token}", f"APT ({state})", available)
        elif channel == "snap":
            available = bool(SNAP)
            add_step("snap", f"sudo snap install {token}", "Snap store", available and token in snap_apps)
        elif channel == "flatpak":
            fid = _flatpak_id(token)
            available = bool(FLATPAK)
            target = fid or token
            add_step("flatpak", f"flatpak install flathub {target}", "Flatpak/Flathub", available)
        elif channel == "appimage":
            path = _find_appimage(token)
            available = path is not None
            add_step(
                "appimage",
                path or "Download AppImage",
                "Portable AppImage (manual)",
                available,
            )

    return plan
