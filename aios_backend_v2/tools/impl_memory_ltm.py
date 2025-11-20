from __future__ import annotations

import os

from .base import Tool

LTM_ENABLED = os.getenv("AIOS_MEMORY_LTM_V1", "off").lower() in {"1", "true", "on"}

if LTM_ENABLED:
    from ..memory import ltm as ltm_store
else:
    ltm_store = None


class MemoryLtmAdd(Tool):
    name = "memory_ltm_add"
    description = "Store a long-term memory snippet (fact, preference, etc.)."
    permissions = []
    params_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "kind": {"type": "string", "enum": ["fact", "preference", "interaction", "note"], "default": "note"},
            "app_tags": {"type": "array", "items": {"type": "string"}},
            "ttl_days": {"type": ["integer", "null"]},
        },
        "required": ["text"],
        "additionalProperties": False,
    }

    returns_schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}, "id": {"type": "string"}, "error": {"type": "string"}},
        "required": ["ok"],
    }

    async def run(self, args):
        if not LTM_ENABLED or ltm_store is None:
            return {"ok": False, "error": "LTM disabled"}
        text = (args.get("text") or "").strip()
        if not text:
            return {"ok": False, "error": "text required"}
        memory = {
            "text": text,
            "kind": args.get("kind") or "note",
            "app_tags": args.get("app_tags") or [],
            "ttl_days": args.get("ttl_days"),
        }
        mem_id = ltm_store.add(memory)
        note = f"[ltm_added:{memory['kind']}:{mem_id}]"
        return {"ok": True, "id": mem_id, "note": note}


class MemoryLtmSearch(Tool):
    name = "memory_ltm_search"
    description = "Search long-term memory via semantic similarity."
    permissions = []
    params_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "k": {"type": "integer"},
        },
        "required": ["query"],
        "additionalProperties": False,
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "results": {
                "type": "array",
                "items": {"type": "object"},
            },
            "error": {"type": "string"},
        },
        "required": ["ok", "results"],
    }

    async def run(self, args):
        if not LTM_ENABLED or ltm_store is None:
            return {"ok": False, "results": [], "error": "LTM disabled"}
        query = (args.get("query") or "").strip()
        if not query:
            return {"ok": False, "results": [], "error": "query required"}
        results = []
        for mem in ltm_store.search(query, args.get("k")):
            results.append(
                {
                    "id": mem.get("id"),
                    "text": mem.get("text"),
                    "summary": mem.get("summary") or mem.get("text"),
                    "kind": mem.get("kind"),
                    "created_ts": mem.get("created_ts"),
                }
            )
        return {"ok": True, "results": results}


class MemoryLtmForget(Tool):
    name = "memory_ltm_forget"
    description = "Delete a memory from the long-term store."
    permissions = []
    params_schema = {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
        "additionalProperties": False,
    }

    returns_schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}, "deleted": {"type": "boolean"}, "error": {"type": "string"}},
        "required": ["ok"],
    }

    async def run(self, args):
        if not LTM_ENABLED or ltm_store is None:
            return {"ok": False, "deleted": False, "error": "LTM disabled"}
        mem_id = (args.get("id") or "").strip()
        if not mem_id:
            return {"ok": False, "deleted": False, "error": "id required"}
        deleted = ltm_store.delete(mem_id)
        return {"ok": True, "deleted": deleted}


class MemoryLtmPrune(Tool):
    name = "memory_ltm_prune"
    description = "Prune long-term memory according to policy (ttl or size)."
    permissions = []
    params_schema = {
        "type": "object",
        "properties": {
            "policy": {"type": "string", "enum": ["ttl", "size"], "default": "size"},
        },
        "additionalProperties": False,
    }

    returns_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "note": {"type": "string"},
            "error": {"type": "string"},
        },
        "required": ["ok"],
    }

    async def run(self, args):
        if not LTM_ENABLED or ltm_store is None:
            return {"ok": False, "note": "", "error": "LTM disabled"}
        policy = args.get("policy") or "size"
        if policy == "size":
            removed = ltm_store.prune()
            return {"ok": True, "note": f"Pruned {removed} memories."}
        # ttl policy placeholder
        return {"ok": True, "note": "TTL pruning not implemented yet."}


tools = [MemoryLtmAdd(), MemoryLtmSearch(), MemoryLtmForget(), MemoryLtmPrune()]
