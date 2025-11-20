from __future__ import annotations

import os
import shutil
import subprocess


def is_hyprland() -> bool:
    if os.getenv("HYPRLAND_INSTANCE_SIGNATURE"):
        return True
    if shutil.which("hyprctl"):
        try:
            subprocess.run(
                ["hyprctl", "instances"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=0.2,
                check=False,
            )
            return True
        except Exception:
            pass
    return False


def compositor_name() -> str:
    if is_hyprland():
        return "hyprland"
    desk = (os.getenv("XDG_CURRENT_DESKTOP") or "").lower()
    sess = (os.getenv("DESKTOP_SESSION") or "").lower()
    if "gnome" in desk or "gnome" in sess:
        return "gnome"
    return "other"

