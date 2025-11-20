from __future__ import annotations

from typing import Any, Dict, List

from ..base import Tool
from .base_cmd import run_command

INTERACTIVE_BLOCKLIST = {
    "htop",
    "top",
    "less",
    "more",
    "nano",
    "vim",
    "vi",
    "watch",
    "man",
    "ssh",
}


def _normalize(cmd: List[str]) -> str:
    if not cmd:
        return ""
    head = cmd[0]
    return head.split("/")[-1].lower()


class RunCommandSafe(Tool):
    name = "run_command_safe"
    description = "Run a read-only shell command (e.g. ls, cat)."
    permissions = ["shell:read"]
    params_schema = {
        "type": "object",
        "properties": {
            "cmd": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command segments, e.g. ['ls','-la']",
            }
        },
        "required": ["cmd"],
        "additionalProperties": False,
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "stdout": {"type": "string"},
            "stderr": {"type": "string"},
            "returncode": {"type": "integer"},
        },
    }

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cmd: List[str] = args["cmd"]
        head = _normalize(cmd)
        if not head:
            return {"ok": False, "stdout": "", "stderr": "Empty command", "returncode": 1}
        if head in INTERACTIVE_BLOCKLIST:
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"Interactive command '{head}' is not supported. Open a terminal instead.",
                "returncode": 126,
            }
        return await run_command(cmd)


tool = RunCommandSafe()
