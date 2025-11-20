from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

from . import db

LOGGER = logging.getLogger(__name__)
_INITIALIZED = False


def init_memory() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    try:
        db.ensure_schema()
        _INITIALIZED = True
    except Exception as exc:
        LOGGER.exception("memory_db_init_failed", exc_info=exc)
        _INITIALIZED = False


def get_pref(key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        value = db.get_pref(key)
        return value if value is not None else default
    except Exception as exc:
        LOGGER.error("memory_db_get_pref_failed", exc_info=exc)
        return default


def set_pref(key: str, value: str) -> None:
    try:
        db.set_pref(key, value)
    except Exception as exc:
        LOGGER.error("memory_db_set_pref_failed", exc_info=exc)


def get_default(kind: str) -> Optional[str]:
    try:
        return db.get_default(kind)
    except Exception as exc:
        LOGGER.error("memory_db_get_default_failed", exc_info=exc)
        return None


def set_default(kind: str, target: str) -> None:
    try:
        db.set_default(kind, target)
    except Exception as exc:
        LOGGER.error("memory_db_set_default_failed", exc_info=exc)


def get_alias(phrase: str) -> Optional[Dict[str, Any]]:
    try:
        return db.get_alias(phrase)
    except Exception as exc:
        LOGGER.error("memory_db_get_alias_failed", exc_info=exc)
        return None


def set_alias(
    phrase: str,
    target: str,
    confidence: float = 1.0,
    status: str = "provisional",
    success_count: int = 0,
) -> None:
    try:
        db.set_alias(phrase, target, confidence, status, success_count)
    except Exception as exc:
        LOGGER.error("memory_db_set_alias_failed", exc_info=exc)


def bulk_upsert_app_index(entries: Iterable[Dict[str, Any]]) -> None:
    try:
        db.bulk_upsert_app_index(entries)
    except Exception as exc:
        LOGGER.error("memory_db_app_index_failed", exc_info=exc)


def search_app_index_by_tag(tag: str, limit: int = 10) -> List[Dict[str, Any]]:
    try:
        return db.search_app_index_by_tag(tag, limit)
    except Exception as exc:
        LOGGER.error("memory_db_search_tag_failed", exc_info=exc)
        return []


def search_app_index_by_name(term: str, limit: int = 10) -> List[Dict[str, Any]]:
    try:
        return db.search_app_index_by_name(term, limit)
    except Exception as exc:
        LOGGER.error("memory_db_search_name_failed", exc_info=exc)
        return []


def list_aliases(limit: int = 10) -> List[Dict[str, Any]]:
    try:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT phrase,target,confidence,status,success_count,created_at FROM aliases "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    except Exception as exc:
        LOGGER.error("memory_db_list_aliases_failed", exc_info=exc)
        return []


def increment_alias_success(phrase: str) -> Optional[Dict[str, Any]]:
    try:
        return db.increment_alias_success(phrase)
    except Exception as exc:
        LOGGER.error("memory_db_alias_success_failed", exc_info=exc)
        return None


def get_user_profile() -> Dict[str, str]:
    try:
        return db.get_user_profile()
    except Exception as exc:
        LOGGER.error("memory_db_get_user_profile_failed", exc_info=exc)
        return {}


def set_user_profile_entry(key: str, value: str) -> None:
    try:
        db.set_user_profile_entry(key, value)
    except Exception as exc:
        LOGGER.error("memory_db_set_user_profile_failed", exc_info=exc)
