from __future__ import annotations

import os
from typing import Any, Dict

from ..base import Tool


class MakeDirectory(Tool):
    name = "mkdir"
    description = "Create a directory (aka 'make folder'/'create folder')."
    permissions = ["fs:write"]
    params_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or workspace-relative path to create",
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "path": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": ["ok", "path"],
    }

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        path = args["path"]
        try:
            os.makedirs(path, exist_ok=True)
            return {"ok": True, "path": path, "message": "directory ensured"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "path": path, "message": str(exc)}


tool = MakeDirectory()
