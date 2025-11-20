from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

try:  # pragma: no cover - optional dependency
    import numpy as np
except Exception:  # noqa: BLE001
    np = None

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import faiss  # type: ignore
except Exception:  # noqa: BLE001
    faiss = None

try:  # pragma: no cover - optional dependency
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # noqa: BLE001
    SentenceTransformer = None


from ..settings import LTM_DIR
from .profile import format_profile_summary

LTM_ENABLED = os.getenv("AIOS_MEMORY_LTM_V1", "off").lower() in {"1", "true", "on"}
EMBED_MODEL_NAME = os.getenv("AIOS_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
STORE_PATH = LTM_DIR
STORE_PATH.mkdir(parents=True, exist_ok=True)
MEM_FILE = STORE_PATH / "memories.json"
MAX_MEMS = int(os.getenv("AIOS_LTM_MAX", "5000") or "5000")
SEARCH_K = int(os.getenv("AIOS_LTM_K", "5") or "5")

_memories: List[Dict[str, object]] = []
_embedding_cache: List[object] = []
_embedder: Optional[SentenceTransformer] = None
_index = None
_SECRET_PATTERN = re.compile(r"(api[_-]?key|bearer\s+[a-z0-9]+|sk-[a-z0-9]{20,})", re.IGNORECASE)


def _load_embedder() -> Optional[SentenceTransformer]:
    global _embedder
    if _embedder is not None:
        return _embedder
    if SentenceTransformer is None:
        LOGGER.warning("ltm_embedder_missing", extra={"model": EMBED_MODEL_NAME})
        return None
    try:
        _embedder = SentenceTransformer(EMBED_MODEL_NAME)
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("ltm_embedder_failed", exc_info=exc)
        _embedder = None
    return _embedder


def _embed(text: str):
    embedder = _load_embedder()
    size = 384
    if embedder is None or np is None:
        vec = [0.0] * size
        for idx, ch in enumerate(text.encode("utf-8")):
            vec[idx % size] += ch / 255.0
        norm = sum(v * v for v in vec) ** 0.5
        if norm:
            vec = [v / norm for v in vec]
        if np is not None:
            return np.asarray(vec, dtype="float32")
        return vec
    vec = embedder.encode([text], normalize_embeddings=True)[0]
    return np.asarray(vec, dtype="float32")


def _rebuild_index() -> None:
    global _index, _embedding_cache
    if not _memories:
        _embedding_cache = []
        _index = None
        return
    _embedding_cache = [_embed(mem.get("text", "")) for mem in _memories]
    if faiss is None or np is None:
        _index = None
        return
    dim = _embedding_cache[0].shape[0]
    index = faiss.IndexFlatIP(dim)
    mat = np.stack(_embedding_cache)
    index.add(mat)
    _index = index


def load() -> None:
    if not MEM_FILE.exists():
        return
    try:
        data = json.loads(MEM_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            _memories.clear()
            _memories.extend(data)
            _rebuild_index()
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("ltm_load_failed", exc_info=exc)


def save() -> None:
    try:
        MEM_FILE.write_text(json.dumps(_memories, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("ltm_save_failed", exc_info=exc)


def add(memory: Dict[str, object]) -> str:
    mem = dict(memory)
    mem.setdefault("id", str(uuid.uuid4()))
    mem.setdefault("created_ts", time.time())
    mem.setdefault("kind", "note")
    mem.setdefault("privacy", "personal")
    mem.setdefault("source", "user")
    mem.setdefault("text", "")
    mem["text"] = _sanitize(mem.get("text", ""))
    mem["summary"] = _summarize_text(str(mem.get("text", "")))
    _memories.append(mem)
    pruned = prune()
    if pruned:
        LOGGER.info("ltm_pruned", extra={"count": pruned})
    _rebuild_index()
    save()
    return mem["id"]  # type: ignore[index]


def search(query: str, k: Optional[int] = None, return_perf: bool = False):
    if not _memories:
        if return_perf:
            return [], {"embed_ms": 0.0, "search_ms": 0.0}
        return []
    limit = min(k or SEARCH_K, 5)
    start_time = time.perf_counter()
    vector = _embed(query)
    embed_ms = (time.perf_counter() - start_time) * 1000
    start_time = time.perf_counter()
    scores = []
    if np is not None and _index is not None:
        vec = vector.reshape(1, -1)
        top_scores, top_idx = _index.search(vec, min(limit, len(_memories)))
        for score, idx in zip(top_scores[0], top_idx[0]):
            if idx >= 0:
                scores.append((float(score), idx))
    else:
        for idx, emb in enumerate(_embedding_cache):
            score = float(_dot(vector, emb))
            scores.append((score, idx))
        scores.sort(reverse=True)
        scores = scores[:limit]
    search_ms = (time.perf_counter() - start_time) * 1000
    results = []
    now = time.time()
    for _, idx in scores:
        mem = _memories[idx]
        if _expired(mem, now):
            continue
        mem_copy = dict(mem)
        summary_text = str(mem_copy.get("summary") or mem_copy.get("text", ""))
        if len(summary_text) > 140:
            mem_copy["summary"] = summary_text[:137] + "..."
        results.append(mem_copy)
    if return_perf:
        return results, {"embed_ms": embed_ms, "search_ms": search_ms}
    return results


def delete(mem_id: str) -> bool:
    for idx, mem in enumerate(_memories):
        if mem.get("id") == mem_id:
            _memories.pop(idx)
            _rebuild_index()
            save()
            return True
    return False


def prune() -> int:
    now = time.time()
    pruned = [mem for mem in _memories if not _expired(mem, now)]
    pruned.sort(key=lambda m: m.get("created_ts", 0))
    removed = len(_memories) - len(pruned)
    while len(pruned) > MAX_MEMS:
        # remove oldest "personal" first
        personal_idx = next((i for i, m in enumerate(pruned) if m.get("privacy") == "personal"), None)
        if personal_idx is not None:
            pruned.pop(personal_idx)
        else:
            pruned.pop(0)
    removed += len(_memories) - len(pruned)
    _memories[:] = pruned
    _rebuild_index()
    save()
    return removed


def summarize(memory: Dict[str, object]) -> str:
    if memory.get("summary"):
        return str(memory["summary"])
    text = str(memory.get("text", ""))
    summary = _summarize_text(text)
    memory["summary"] = summary
    return summary


def _summarize_text(text: str) -> str:
    if not text:
        return ""
    sentence = text.split(".", 1)[0].strip()
    if not sentence:
        sentence = text[:200]
    words = sentence.split()
    nouns = [w for w in words if w[:1].isupper() or w.endswith("ing")]
    extra = " ".join(nouns[:4])
    summary = sentence
    if extra and extra not in summary:
        summary = f"{sentence} ({extra})"
    if len(summary) > 200:
        summary = summary[:197] + "..."
    return summary


def _expired(mem: Dict[str, object], now: float) -> bool:
    ttl = mem.get("ttl_days")
    if not ttl:
        return False
    created = mem.get("created_ts", 0)
    return (now - created) > (float(ttl) * 86400)


def _sanitize(text: str) -> str:
    return _SECRET_PATTERN.sub("[redacted]", str(text))


def _dot(a, b) -> float:
    if np is not None:
        return float(np.dot(a, b))
    return float(sum(float(x) * float(y) for x, y in zip(a, b)))


load()

def store_entry(summary: str, memory_type: str, strength: float, source: str = "memory_evaluator") -> str:
    entry = {
        "text": summary,
        "kind": memory_type,
        "strength": strength,
        "source": source,
        "created_ts": time.time(),
    }
    return add(entry)

def _latest_entry_by_kind(kind: str) -> Optional[Dict[str, object]]:
    for mem in reversed(_memories):
        if mem.get("kind") == kind:
            return dict(mem)
    return None


def load_user_profile_entry() -> Optional[Dict[str, object]]:
    return _latest_entry_by_kind("user_profile")


def load_user_profile_dict() -> Dict[str, str]:
    entry = load_user_profile_entry()
    if not entry:
        return {}
    text = entry.get("text")
    if not isinstance(text, str):
        return {}
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items() if isinstance(v, str) and v}
    except json.JSONDecodeError:
        pass
    return {}


def _replace_memory_entry(mem_id: str, new_entry: Dict[str, object]) -> str:
    updated = dict(new_entry)
    updated.setdefault("id", mem_id)
    updated.setdefault("created_ts", time.time())
    updated.setdefault("kind", "note")
    updated.setdefault("source", "user")
    updated.setdefault("text", "")
    updated["text"] = _sanitize(updated.get("text", ""))
    updated["summary"] = updated.get("summary") or _summarize_text(str(updated.get("text", "")))
    for idx, mem in enumerate(_memories):
        if mem.get("id") == mem_id:
            _memories[idx] = updated
            _rebuild_index()
            save()
            return mem_id
    return add(updated)


def save_user_profile(profile: Dict[str, str], source: str = "memory_evaluator") -> str:
    cleaned = {k: v for k, v in profile.items() if v}
    summary = format_profile_summary(cleaned)
    entry = {
        "text": json.dumps(cleaned, ensure_ascii=False),
        "summary": summary,
        "kind": "user_profile",
        "strength": 0.9,
        "source": source,
        "created_ts": time.time(),
    }
    existing = load_user_profile_entry()
    if existing and existing.get("id"):
        return _replace_memory_entry(str(existing["id"]), entry)
    return add(entry)
