from __future__ import annotations

from typing import Any, Dict

from .base import Tool
from ..util.app_resolver import resolve_app_v2


class PkgInfo(Tool):
    name = "pkg_info"
    description = "Report how AIOS would resolve an app/package across channels."
    permissions = ["shell:read"]
    params_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "channel": {"type": "string", "enum": ["apt", "snap", "flatpak", "appimage"]},
        },
        "required": ["name"],
        "additionalProperties": False,
    }
    returns_schema = {"type": "object"}

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = (args.get("name") or "").strip()
        if not name:
            return {"ok": False, "error": "name is required"}
        info = resolve_app_v2(name, args.get("channel"))
        info["ok"] = info.get("ok", False)
        info["name"] = name
        return info


tool = PkgInfo()
