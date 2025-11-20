from __future__ import annotations

import asyncio
import os
import subprocess
from typing import Any, Dict, List

from .base import Tool
from ..util.session import compositor_name
from ..runtime import cache as runtime_cache

DEFAULT_TERMINAL = os.getenv("AIOS_TERMINAL", "kitty")
DEFAULT_WORKSPACE = int(os.getenv("AIOS_TUI_WORKSPACE", "9") or "9")
TERMINAL_CHOICES = {"kitty", "foot", "gnome-terminal", "alacritty"}
TUI_FALLBACK_ORDER = ["kitty", "alacritty", "foot", "gnome-terminal"]


def _dispatch_workspace(workspace: int) -> None:
    if workspace <= 0:
        return
    try:
        subprocess.Popen(
            ["hyprctl", "dispatch", "workspace", str(workspace)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _build_argv(term: str, program: str, args: List[str]) -> List[str] | None:
    if term == "kitty":
        return ["kitty", "-e", program, *args]
    if term == "foot":
        return ["foot", program, *args]
    if term == "gnome-terminal":
        return ["gnome-terminal", "--", program, *args]
    if term == "alacritty":
        return ["alacritty", "-e", program, *args]
    return None


def _launch(term: str, program: str, args: List[str]) -> Dict[str, Any]:
    argv = _build_argv(term, program, args)
    if argv is None:
        return {"ok": False, "error": f"unsupported terminal '{term}'"}
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )
        return {"ok": True, "pid": proc.pid, "terminal": term}
    except FileNotFoundError:
        return {"ok": False, "error": f"terminal '{term}' not found"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


class OpenTerminal(Tool):
    name = "open_terminal"
    description = "Open a terminal window and optionally run a program."
    permissions = ["apps:launch"]
    params_schema = {
        "type": "object",
        "properties": {
            "program": {"type": "string"},
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
            },
            "workspace": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": DEFAULT_WORKSPACE,
            },
            "terminal": {
                "type": "string",
                "enum": list(TERMINAL_CHOICES),
                "default": DEFAULT_TERMINAL,
            },
        },
        "required": ["program"],
        "additionalProperties": False,
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "pid": {"type": "integer"},
            "terminal": {"type": "string"},
            "workspace": {"type": "integer"},
            "program": {"type": "string"},
            "error": {"type": "string"},
            "compositor": {"type": "string"},
            "note": {"type": "string"},
        },
    }

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        program = (args.get("program") or "").strip()
        if not program:
            return {"ok": False, "error": "program is required"}

        cmd_args = [str(part) for part in (args.get("args") or [])]
        workspace_raw = args.get("workspace", DEFAULT_WORKSPACE)
        try:
            workspace = max(1, min(10, int(workspace_raw)))
        except (TypeError, ValueError):
            workspace = DEFAULT_WORKSPACE

        requested_terminal = (args.get("terminal") or DEFAULT_TERMINAL).lower()
        terminal = requested_terminal if requested_terminal in TERMINAL_CHOICES else DEFAULT_TERMINAL

        comp = compositor_name()
        if comp == "hyprland":
            _dispatch_workspace(workspace)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _launch, terminal, program, cmd_args)

        if not result.get("ok"):
            for candidate in TUI_FALLBACK_ORDER:
                if candidate == terminal:
                    continue
                fallback = await loop.run_in_executor(None, _launch, candidate, program, cmd_args)
                if fallback.get("ok"):
                    result = fallback
                    terminal = candidate
                    break

        if result.get("ok"):
            if comp == "hyprland":
                note = f"Opening {program} in {terminal} on workspace {workspace}"
            elif comp == "gnome":
                note = f"Opening {program} in {terminal} (current GNOME workspace)"
            else:
                note = f"Opening {program} in {terminal}"
            result.update(
                {
                    "workspace": workspace,
                    "program": program,
                    "terminal": terminal,
                    "compositor": comp,
                    "note": note,
                }
            )
            runtime_cache.push_recent_launch(program, f"terminal:{terminal}")
            if comp == "hyprland":
                runtime_cache.set_last_ws("hyprland", workspace)
        else:
            result.setdefault("compositor", comp)
        return result


tool = OpenTerminal()
