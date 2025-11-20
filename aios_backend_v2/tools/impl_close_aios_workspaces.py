from __future__ import annotations

from typing import Any, Dict

from .base import Tool
from ..util.session import compositor_name
from ..util.hypr import (
    listed_aios_workspaces,
    workspace_has_windows,
    switch_workspace,
    unmark_aios_workspace,
)


class CloseAiosWorkspaces(Tool):
    name = "close_empty_aios_workspaces"
    description = "Close Hyprland workspaces created by AIOS that are currently empty."
    permissions = ["apps:launch"]
    params_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    returns_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "closed": {"type": "array", "items": {"type": "integer"}},
            "kept": {"type": "array", "items": {"type": "integer"}},
            "note": {"type": "string"},
        },
    }

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        comp = compositor_name()
        if comp != "hyprland":
            return {"ok": True, "closed": [], "kept": [], "note": "Not Hyprland; nothing to clean."}

        closed, kept = [], []
        for ws in listed_aios_workspaces():
            if workspace_has_windows(ws):
                kept.append(ws)
                continue
            switch_workspace("r+")
            closed.append(ws)
            unmark_aios_workspace(ws)
        note = f"Closed {len(closed)} empty AIOS workspaces."
        if kept:
            note += f" {len(kept)} kept (in use)."
        return {"ok": True, "closed": closed, "kept": kept, "note": note}


tool = CloseAiosWorkspaces()
