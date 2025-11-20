from __future__ import annotations

import os
from typing import Any, Dict

from ..base import Tool


class TouchFile(Tool):
    name = "touch"
    description = "Create/update a file (aka 'create file', 'touch file')."
    permissions = ["fs:write"]
    params_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or workspace-relative file path",
            },
            "content": {"type": "string", "description": "Optional text content"},
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
        content = args.get("content")
        try:
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            mode = "w" if content is not None else "a"
            with open(path, mode, encoding="utf-8") as fh:
                if content is not None:
                    fh.write(content)
            return {"ok": True, "path": path, "message": "file touched"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "path": path, "message": str(exc)}


tool = TouchFile()
