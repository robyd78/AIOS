import os

from .base import Tool

SYSTEM_CARD_ENABLED = os.getenv("AIOS_SYSTEM_CARD_V1", "off").lower() in {"1", "true", "on"}
MEMORY_DB_ENABLED = os.getenv("AIOS_MEMORY_DB_V1", "off").lower() in {"1", "true", "on"}
APP_INDEX_ENABLED = os.getenv("AIOS_APP_INDEX_V1", "off").lower() in {"1", "true", "on"}

if SYSTEM_CARD_ENABLED:
    from ..system_card.card import invalidate_cache as invalidate_system_card_cache
else:
    def invalidate_system_card_cache():
        return None

if APP_INDEX_ENABLED and MEMORY_DB_ENABLED:
    from ..indexer import apps as app_indexer
else:
    app_indexer = None

try:
    from ..persona.core import invalidate_persona_card
except Exception:  # pragma: no cover - optional
    def invalidate_persona_card():
        return None

class SystemRefresh(Tool):
    name = "system_refresh"
    description = "Refresh the cached system card and application index snapshots."
    permissions = []
    params_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    returns_schema = {"type": "object", "properties": {"ok": {"type": "boolean"}, "note": {"type": "string"}}, "required": ["ok"]}

    async def run(self, args):
        if not SYSTEM_CARD_ENABLED and not (APP_INDEX_ENABLED and MEMORY_DB_ENABLED):
            return {"ok": True, "note": "disabled", "refreshed": False}

        refreshed = False
        if APP_INDEX_ENABLED and MEMORY_DB_ENABLED and app_indexer:
            refreshed = app_indexer.refresh(force=True) or refreshed

        if SYSTEM_CARD_ENABLED:
            invalidate_system_card_cache()
            refreshed = True
        invalidate_persona_card()

        return {"ok": True, "note": "refreshed" if refreshed else "no-op", "refreshed": refreshed}


tool = SystemRefresh()
