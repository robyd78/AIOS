from __future__ import annotations

from typing import Any, Dict

from .base import Tool
from ..util.pkg_plan import build_install_plan


class PkgPlanInstall(Tool):
    name = "pkg_plan_install"
    description = "Show the install plan for an application across apt/snap/flatpak/appimage."
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
    returns_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "name": {"type": "string"},
            "plan": {
                "type": "array",
                "items": {"type": "object"},
            },
        },
    }

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        target = (args.get("name") or "").strip()
        if not target:
            return {"ok": False, "error": "name is required"}
        plan = build_install_plan(target, args.get("channel"))
        return {"ok": True, "name": target, "plan": plan}


tool = PkgPlanInstall()
