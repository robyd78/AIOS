from __future__ import annotations

import collections
import threading
import time
from typing import Deque, Dict, List, Optional, Tuple, TYPE_CHECKING

MAX_ENTRIES = 50
TTL_SECONDS = 120

_recent_launches: Deque[Dict[str, object]] = collections.deque()
_last_workspace_ids: Dict[str, Tuple[int, float]] = {}
_last_alias_hits: Dict[str, Tuple[str, float]] = {}
_clarify_choices: Dict[str, Tuple[set, float]] = {}
_alias_promotions: Dict[str, Tuple[bool, float]] = {}
_conversation_turns: Deque[Dict[str, str]] = collections.deque()
_last_system_prompt: str = ""
if TYPE_CHECKING:  # pragma: no cover
    from ..context.snapshot import ContextSnapshot

_last_context_snapshot: Optional["ContextSnapshot"] = None
_cache_hits = 0
_cache_misses = 0
_lock = threading.Lock()
_stats_lock = threading.Lock()


def _now() -> float:
    return time.time()


def _prune_recent(now: float) -> None:
    while _recent_launches:
        entry = _recent_launches[0]
        if now - entry["ts"] <= TTL_SECONDS and len(_recent_launches) <= MAX_ENTRIES:
            break
        _recent_launches.popleft()


def _prune_dict(store: Dict[str, Tuple[object, float]], now: float) -> None:
    expired = [key for key, (_, ts) in store.items() if now - ts > TTL_SECONDS]
    for key in expired:
        store.pop(key, None)


def _record(hit: bool) -> None:
    global _cache_hits, _cache_misses
    with _stats_lock:
        if hit:
            _cache_hits += 1
        else:
            _cache_misses += 1


def push_recent_launch(app_id: str, channel: Optional[str]) -> None:
    if not app_id:
        return
    now = _now()
    with _lock:
        _recent_launches.append(
            {
                "app_id": app_id,
                "channel": channel,
                "ts": now,
            }
        )
        _prune_recent(now)


def get_recent_launches() -> List[Dict[str, object]]:
    now = _now()
    with _lock:
        _prune_recent(now)
        data = list(_recent_launches)
    _record(bool(data))
    return data


def set_last_ws(compositor: str, workspace_id: int) -> None:
    if not compositor:
        return
    now = _now()
    with _lock:
        _last_workspace_ids[compositor] = (workspace_id, now)


def get_last_ws(compositor: str) -> Optional[int]:
    if not compositor:
        _record(False)
        return None
    now = _now()
    with _lock:
        _prune_dict(_last_workspace_ids, now)
        entry = _last_workspace_ids.get(compositor)
    hit = entry is not None
    _record(hit)
    if hit:
        return entry[0]
    return None


def set_last_alias_hit(phrase: str, target: str) -> None:
    if not phrase or not target:
        return
    now = _now()
    key = phrase.lower()
    with _lock:
        _last_alias_hits[key] = (target, now)


def get_last_alias_hit(phrase: str) -> Optional[str]:
    if not phrase:
        _record(False)
        return None
    now = _now()
    key = phrase.lower()
    with _lock:
        _prune_dict(_last_alias_hits, now)
        entry = _last_alias_hits.get(key)
    hit = entry is not None
    _record(hit)
    if hit:
        return entry[0]
    return None


def stats_snapshot() -> Dict[str, int]:
    with _stats_lock:
        hits = _cache_hits
        misses = _cache_misses
    return {"hits": hits, "misses": misses}


def push_conversation_turn(user_text: str, assistant_text: str) -> None:
    if not (user_text or assistant_text):
        return
    with _lock:
        _conversation_turns.append(
            {
                "user": user_text or "",
                "assistant": assistant_text or "",
                "ts": _now(),
            }
        )
        while len(_conversation_turns) > 5:
            _conversation_turns.popleft()


def get_conversation_turns() -> List[Dict[str, str]]:
    with _lock:
        return list(_conversation_turns)


def set_last_system_prompt(prompt: str) -> None:
    global _last_system_prompt
    with _lock:
        _last_system_prompt = prompt or ""


def get_last_system_prompt() -> str:
    with _lock:
        return _last_system_prompt


def set_last_context_snapshot(snapshot) -> None:
    """Store the latest context snapshot (ContextSnapshot instance)."""
    global _last_context_snapshot
    with _lock:
        _last_context_snapshot = snapshot


def get_last_context_snapshot() -> Dict[str, object]:
    with _lock:
        snapshot = _last_context_snapshot
    if snapshot is None:
        return {}
    if hasattr(snapshot, "public_view"):
        return snapshot.public_view()
    return dict(snapshot)


def store_clarify_options(option_ids: List[str]) -> None:
    if not option_ids:
        return
    now = _now()
    with _lock:
        _clarify_choices["_global"] = (set(option_ids), now)


def consume_clarify_choice(app_id: Optional[str]) -> bool:
    if not app_id:
        return False
    now = _now()
    with _lock:
        bucket = _clarify_choices.get("_global")
        if not bucket:
            return False
        options, ts = bucket
        if now - ts > TTL_SECONDS:
            _clarify_choices.pop("_global", None)
            return False
        if app_id in options:
            options.remove(app_id)
            if not options:
                _clarify_choices.pop("_global", None)
            return True
    return False


def flag_alias_promoted(app_id: Optional[str]) -> None:
    if not app_id:
        return
    with _lock:
        _alias_promotions[app_id] = (True, _now())


def consume_alias_promoted(app_id: Optional[str]) -> bool:
    if not app_id:
        return False
    now = _now()
    with _lock:
        _prune_dict(_alias_promotions, now)
        if app_id in _alias_promotions:
            _alias_promotions.pop(app_id, None)
            return True
    return False
