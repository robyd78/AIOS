from __future__ import annotations

from .base import Tool
from .. import logs


class LogsStatus(Tool):
    name = "logs_status"
    description = "Report current sizes and last rotation times for AIOS logs."
    permissions = []
    params_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    returns_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "logs": {"type": "object"},
        },
        "required": ["ok", "logs"],
    }

    async def run(self, args):
        return {"ok": True, "logs": logs.get_log_stats()}


tool = LogsStatus()
