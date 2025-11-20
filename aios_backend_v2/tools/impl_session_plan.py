from __future__ import annotations

import glob
import os
import pathlib
import shutil
import subprocess
from typing import Any, Dict, List

from .base import Tool
from ..util.session import compositor_name


def _list_sessions():
    wl = sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob("/usr/share/wayland-sessions/*.desktop")
    )
    xl = sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob("/usr/share/xsessions/*.desktop")
    )
    return {"wayland": wl, "x11": xl}


def _detect_dm():
    if shutil.which("gdm"):
        return "gdm"
    if shutil.which("lightdm"):
        return "lightdm"
    if shutil.which("sddm"):
        return "sddm"
    for name in ("gdm", "lightdm", "sddm"):
        try:
            out = subprocess.check_output(["ps", "-C", name, "-o", "comm="]).decode().strip()
            if out:
                return name
        except Exception:
            continue
    return "unknown"


def _dmrc_path():
    return pathlib.Path.home() / ".dmrc"


class SessionSwitchPlan(Tool):
    name = "session_switch_plan"
    description = "Plan a compositor/desktop session change for next login (no forced logout)."
    permissions = ["shell:read"]
    params_schema = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Session name (e.g., hyprland, gnome)"},
        },
        "required": ["target"],
        "additionalProperties": False,
    }
    returns_schema = {"type": "object"}

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        target = (args.get("target") or "").strip()
        sessions = _list_sessions()
        available = set(sessions["wayland"]) | set(sessions["x11"])
        current = compositor_name()
        dm = _detect_dm()

        if target not in available:
            return {
                "ok": False,
                "error": f"session '{target}' not found",
                "available": sessions,
                "dm": dm,
                "current": current,
            }

        plan: Dict[str, Any] = {
            "ok": True,
            "current": current,
            "target": target,
            "dm": dm,
            "available": sessions,
            "steps": [],
        }

        if dm == "lightdm":
            plan["steps"].append(
                {
                    "type": "write_file",
                    "path": str(_dmrc_path()),
                    "content": f"[Desktop]\\nSession={target}\\n",
                    "description": "Set LightDM default session via ~/.dmrc",
                }
            )
            plan["post_note"] = "Logout or reboot to apply the new session."
            return plan

        plan["steps"].append(
            {
                "type": "command",
                "sudo": True,
                "cmd": "sudo loginctl terminate-user $USER  # logout when ready",
            }
        )
        if dm == "gdm":
            plan["steps"].append(
                {
                    "type": "command",
                    "sudo": True,
                    "cmd": f"sudo sh -c 'mkdir -p /var/lib/AccountsService/users && printf \"[User]\\nXSession={target}\\n\" > /var/lib/AccountsService/users/$USER'",
                    "description": "Set default session for GDM via AccountsService",
                }
            )
            plan["post_note"] = "GDM typically requires admin privileges to change the default session."
        else:
            plan["post_note"] = "Review the suggested commands; apply them manually before your next login."
        return plan


tool = SessionSwitchPlan()
