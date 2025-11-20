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
}


def _normalize(cmd: List[str]) -> str:
    if not cmd:
        return ""
    return cmd[0].split("/")[-1].lower()


class RunCommandRisky(Tool):
    name = "run_command_risky"
    description = "Run a shell command that may modify the system (mkdir, touch, apt, etc.)."
    permissions = ["shell:write"]
    params_schema = {
        "type": "object",
        "properties": {
            "cmd": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command segments, e.g. ['mkdir','-p','test']",
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
            "command": {"type": "string"},
        },
    }

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cmd: List[str] = args["cmd"]
        head = _normalize(cmd)
        if not head:
            return {"ok": False, "stdout": "", "stderr": "Empty command", "returncode": 1, "command": ""}
        if head in INTERACTIVE_BLOCKLIST:
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"Interactive command '{head}' is blocked. Open a terminal if you need it.",
                "returncode": 126,
                "command": "",
            }
        return await run_command(cmd)


tool = RunCommandRisky()
