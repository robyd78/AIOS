from __future__ import annotations

from typing import Any, Dict

from .base import Tool
from ..util.app_resolver import resolve_app


class ResolveAppDebug(Tool):
    name = "resolve_app_debug"
    description = "Explain how open_app would resolve an application without launching it."
    permissions = ["shell:read"]
    params_schema = {
        "type": "object",
        "properties": {"app": {"type": "string"}},
        "required": ["app"],
        "additionalProperties": False,
    }
    returns_schema = {"type": "object"}

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        app = (args.get("app") or "").strip()
        if not app:
            return {"ok": False, "error": "app is required"}
        res = resolve_app(app)
        res["ok"] = res.get("ok", False)
        return res


tool = ResolveAppDebug()
