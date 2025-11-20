from __future__ import annotations

import json
import os
import pathlib
import time
from typing import Any, Dict, Optional

from .settings import LOG_DIR

LOG_PATH = os.path.join(LOG_DIR, "tools.ndjson")
CHAT_LOG_PATH = os.path.join(LOG_DIR, "chat_turns.ndjson")
MAX_FIELD_BYTES = 4096
MAX_LOG_BYTES = 10 * 1024 * 1024
_LAST_ROTATION: Dict[str, float] = {}


def _ensure_log_dir() -> None:
    pathlib.Path(LOG_DIR).mkdir(parents=True, exist_ok=True)


def log_tool_execution(
    name: str,
    args: Dict[str, Any],
    *,
    ok: bool,
    result: Dict[str, Any] | None = None,
    error: str | None = None,
    duration_ms: float | None = None,
) -> None:
    _ensure_log_dir()
    _rotate_if_needed(LOG_PATH)
    entry = {
        "ts": time.time(),
        "tool": name,
        "args": args,
        "ok": ok,
        "duration_ms": duration_ms,
    }
    if result is not None:
        entry["result"] = result
    if error:
        entry["error"] = error
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def log_chat_turn(data: Dict[str, Any]) -> None:
    _ensure_log_dir()
    _rotate_if_needed(CHAT_LOG_PATH)
    entry = {"ts": time.time()}
    entry.update(data)
    _truncate_large_fields(entry)
    with open(CHAT_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _truncate_large_fields(entry: Dict[str, Any]) -> None:
    for key, value in list(entry.items()):
        truncated = _maybe_truncate(value)
        if truncated is not None:
            entry[key] = truncated


def _maybe_truncate(value: Any) -> Any:
    if isinstance(value, str):
        encoded = value.encode("utf-8")
        if len(encoded) > MAX_FIELD_BYTES:
            trimmed = encoded[: MAX_FIELD_BYTES - 15].decode("utf-8", errors="ignore")
            return f"{trimmed}...[truncated]"
        return value
    if isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, ensure_ascii=False)
        encoded = text.encode("utf-8")
        if len(encoded) > MAX_FIELD_BYTES:
            trimmed = encoded[: MAX_FIELD_BYTES - 15].decode("utf-8", errors="ignore")
            return f"{trimmed}...[truncated]"
        return value
    if isinstance(value, bytes):
        if len(value) > MAX_FIELD_BYTES:
            return f"{value[: MAX_FIELD_BYTES - 15]!r}...[truncated]"
        return value.decode("utf-8", errors="ignore")
    return value


def _rotate_if_needed(path: str) -> None:
    try:
        if not os.path.exists(path):
            return
        size = os.path.getsize(path)
        if size < MAX_LOG_BYTES:
            return
        backup1 = f"{path}.1"
        backup2 = f"{path}.2"
        if os.path.exists(backup2):
            os.remove(backup2)
        if os.path.exists(backup1):
            os.replace(backup1, backup2)
        os.replace(path, backup1)
        _LAST_ROTATION[path] = time.time()
    except OSError:
        pass


def get_log_stats() -> Dict[str, Dict[str, Optional[float]]]:
    stats = {}
    for label, path in (("chat", CHAT_LOG_PATH), ("tools", LOG_PATH)):
        size = os.path.getsize(path) if os.path.exists(path) else 0
        stats[label] = {
            "size": size,
            "last_rotation": _LAST_ROTATION.get(path),
        }
    return stats
