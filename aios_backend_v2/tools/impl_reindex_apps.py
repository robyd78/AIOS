from __future__ import annotations

from typing import Any, Dict

from .base import Tool
from ..indexer import apps as apps_indexer


class ReindexApps(Tool):
    name = "reindex_apps"
    description = "Re-scan desktop/flatpak/snap apps and refresh the local index."
    permissions = ["shell:read"]
    params_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    returns_schema = {"type": "object"}

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        apps_indexer.reindex_apps()
        return {"ok": True}


tool = ReindexApps()
