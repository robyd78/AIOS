from __future__ import annotations

from typing import Any, Dict

from .base import Tool
from ..lex.gazetteer import GAZETTEER, canon_app_name


class PkgSearch(Tool):
    name = "pkg_search"
    description = "List canonical matches for an application/package alias."
    permissions = ["shell:read"]
    params_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    }
    returns_schema = {"type": "object"}

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = (args.get("query") or "").strip()
        if not query:
            return {"ok": False, "error": "query is required"}
        matches = []
        canon, conf = canon_app_name(query)
        if canon:
            matches.append({"canonical": canon, "confidence": conf, "aliases": GAZETTEER.get(canon, [])})
        return {"ok": True, "matches": matches}


tool = PkgSearch()
