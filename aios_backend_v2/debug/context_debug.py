from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from .. import flag
from ..runtime import cache as runtime_cache

DEBUG_CONTEXT_ENABLED = flag("AIOS_DEBUG_CONTEXT")

router = APIRouter()


@router.get("/debug/context")
def get_debug_context() -> Dict[str, Any]:
    if not DEBUG_CONTEXT_ENABLED:
        raise HTTPException(status_code=404, detail="context debug disabled")
    snapshot = runtime_cache.get_last_context_snapshot()
    if not snapshot:
        return {
            "ok": True,
            "updated_ts": None,
            "message": "No context snapshot recorded yet. Trigger /chat to populate.",
        }
    return {
        "ok": True,
        "updated_ts": snapshot.get("updated_ts"),
        "context": snapshot,
        "server_time": time.time(),
    }
