from __future__ import annotations

from .base import Tool
from ..runtime import cache as runtime_cache


class PromptDump(Tool):
    name = "prompt_dump"
    description = "Show the first part of the current system prompt for debugging."
    permissions = []
    params_schema = {"type": "object", "properties": {}, "additionalProperties": False}

    returns_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "prompt": {"type": "string"},
            "truncated": {"type": "boolean"},
        },
        "required": ["ok", "prompt", "truncated"],
    }

    async def run(self, args):
        prompt = runtime_cache.get_last_system_prompt()
        if not prompt:
            return {"ok": False, "prompt": "", "truncated": False, "error": "no prompt available"}
        encoded = prompt.encode("utf-8")
        limit = 1500
        truncated = len(encoded) > limit
        if truncated:
            prompt = encoded[: limit - 15].decode("utf-8", errors="ignore") + "...[truncated]"
        return {"ok": True, "prompt": prompt, "truncated": truncated}


tool = PromptDump()
