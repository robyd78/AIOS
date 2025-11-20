import asyncio
import os
import subprocess
import time
from typing import Any, Dict, List

from .base import Tool
from ..util.session import compositor_name
from ..util.app_resolver import resolve_app, resolve_app_v2
from ..util.pkg_plan import build_install_plan
from ..util.hypr import (
    pick_free_workspace,
    mark_aios_workspace,
    listed_aios_workspaces,
    workspace_has_windows,
    switch_workspace,
)
from ..runtime import cache as runtime_cache


RESOLVER_V2_ENABLED = os.getenv("AIOS_RESOLVER_V2", "off").lower() in {"1", "true", "on"}
PKG_TOOLS_ENABLED = os.getenv("AIOS_PKG_TOOLS", "off").lower() in {"1", "true", "on"}


class OpenApp(Tool):
    name = "open_app"
    description = "Open an application by desktop id/name."
    permissions = ["apps:launch"]
    params_schema = {
        "type": "object",
        "properties": {
            "app": {
                "type": "string",
                "description": "Desktop file id or common name, e.g. 'org.gnome.Nautilus'",
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
            },
            "fullscreen": {"type": "boolean", "default": False},
            "aios_workspace": {
                "type": "string",
                "enum": ["auto", "none"],
                "default": "auto",
            },
        },
        "required": ["app"],
        "additionalProperties": False,
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "app": {"type": "string"},
            "note": {"type": "string"},
        },
        "required": ["ok"],
    }

    FULLSCREEN_ARGS = {
        "kitty": ["--start-as=fullscreen"],
        "gnome-terminal": ["--full-screen"],
        "foot": ["--maximized"],
        "mpv": ["--fullscreen"],
        "vlc": ["--fullscreen"],
        "firefox": ["--kiosk"],
    }

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        app = args.get("app") or args.get("app_name") or args.get("name")
        if not app:
            return {"ok": False, "app": None, "error": "app is required"}
        extra: List[str] = list(args.get("args") or [])
        fullscreen = bool(args.get("fullscreen"))
        workspace_mode = args.get("aios_workspace", "auto")
        comp = compositor_name()

        resolver_start = time.perf_counter()
        resolver = resolve_app_v2(app) if RESOLVER_V2_ENABLED else resolve_app(app)
        resolver_ms = (time.perf_counter() - resolver_start) * 1000
        if not resolver.get("ok"):
            plan = build_install_plan(app, args.get("channel")) if PKG_TOOLS_ENABLED else []
            return {
                "ok": False,
                "app": app,
                "error": resolver.get("error", f"app '{app}' not found"),
                "hints": resolver.get("hints", []),
                "plan": plan,
                "resolver_ms": resolver_ms,
                "alias_promoted": False,
            }
        base_cmd = list(resolver.get("cmd") or [])
        if not base_cmd:
            return {"ok": False, "app": app, "error": "resolver returned empty command"}

        if fullscreen and app in self.FULLSCREEN_ARGS:
            extra = self.FULLSCREEN_ARGS[app] + extra

        workspace_used = None
        if comp == "hyprland" and workspace_mode == "auto":
            try:
                reuse = None
                tagged = listed_aios_workspaces()
                for ws in reversed(tagged):
                    if not workspace_has_windows(ws):
                        reuse = ws
                        break
                if reuse is None:
                    workspace_used = pick_free_workspace()
                    mark_aios_workspace(workspace_used)
                else:
                    workspace_used = reuse
                switch_workspace(workspace_used)
            except Exception:
                workspace_used = None

        command = base_cmd + extra
        try:
            proc = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                return {
                    "ok": False,
                    "app": app,
                    "error": stderr.decode("utf-8", "ignore") or f"launch failed with code {proc.returncode}",
                    "command": " ".join(command),
                }
        except FileNotFoundError as exc:
            return {"ok": False, "app": app, "error": str(exc)}

        if comp == "hyprland" and fullscreen:
            asyncio.create_task(_hypr_fullscreen_after_delay())

        source = resolver.get("source", "command")
        channel = resolver.get("channel")
        descriptor = channel or source
        note = f"Opening {app} via {descriptor}"
        if comp == "hyprland":
            target_ws = workspace_used or "current"
            note += f" on workspace {target_ws}"
            if fullscreen:
                note += " (fullscreen)"
        elif comp == "gnome":
            if fullscreen:
                note += " fullscreen"
            note += " (current GNOME workspace)"
        else:
            if fullscreen:
                note += " fullscreen"

        runtime_cache.push_recent_launch(app, channel or source)
        if comp == "hyprland" and workspace_used:
            runtime_cache.set_last_ws("hyprland", workspace_used)

        alias_promoted = runtime_cache.consume_alias_promoted(app)
        return {
            "ok": True,
            "app": app,
            "note": note,
            "command": " ".join(command),
            "source": source,
            "channel": channel,
            "resolver_ms": resolver_ms,
            "alias_promoted": alias_promoted,
        }


async def _hypr_fullscreen_after_delay():
    try:
        await asyncio.sleep(0.25)
        subprocess.Popen(
            ["hyprctl", "dispatch", "fullscreen", "1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


tool = OpenApp()
