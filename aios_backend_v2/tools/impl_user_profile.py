import os

from .base import Tool

MEMORY_DB_ENABLED = os.getenv("AIOS_MEMORY_DB_V1", "off").lower() in {"1", "true", "on"}

if MEMORY_DB_ENABLED:
    from ..memory import store as memory_store
else:
    memory_store = None


class UserProfileSet(Tool):
    name = "user_profile.set"
    description = "Store a user profile preference such as name, tone, or style."
    permissions = []
    params_schema = {
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "string"},
        },
        "required": ["key", "value"],
        "additionalProperties": False,
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "key": {"type": "string"},
            "value": {"type": "string"},
            "error": {"type": "string"},
        },
        "required": ["ok"],
    }

    async def run(self, args):
        if memory_store is None:
            return {"ok": False, "error": "memory disabled"}
        key = str(args.get("key") or "").strip().lower()
        value = str(args.get("value") or "").strip()
        if not key:
            return {"ok": False, "error": "key required"}
        if not value:
            return {"ok": False, "error": "value required"}
        memory_store.set_user_profile_entry(key, value)
        return {"ok": True, "key": key, "value": value}


tool = UserProfileSet()
