from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from typing import Dict, Iterable, List, Optional

from ..settings import DB_PATH

LOGGER = logging.getLogger(__name__)
SCHEMA_VERSION = 2

_CONN: Optional[sqlite3.Connection] = None
_LOCK = threading.Lock()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_connection() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        with _LOCK:
            if _CONN is None:
                _CONN = _connect()
    return _CONN


def ensure_schema() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA user_version;")
    version = cur.fetchone()[0]
    if version == 0:
        _create_schema(cur)
        cur.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
        LOGGER.info("memory_db_schema_initialized", extra={"schema_version": SCHEMA_VERSION, "path": str(DB_PATH)})
    elif version < SCHEMA_VERSION:
        _migrate_schema(cur, version, SCHEMA_VERSION)
        cur.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
        LOGGER.info(
            "memory_db_schema_migrated",
            extra={"from": version, "to": SCHEMA_VERSION, "path": str(DB_PATH)},
        )
    elif version > SCHEMA_VERSION:
        LOGGER.warning("memory_db_schema_newer", extra={"found": version, "expected": SCHEMA_VERSION})
    else:
        LOGGER.info("memory_db_schema_ready", extra={"schema_version": version, "path": str(DB_PATH)})


def _create_schema(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS prefs (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS aliases (
            phrase TEXT PRIMARY KEY,
            target TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            status TEXT DEFAULT 'provisional',
            success_count INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now'))
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS defaults (
            kind TEXT PRIMARY KEY,
            target TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS app_index (
            id TEXT PRIMARY KEY,
            name TEXT,
            generic TEXT,
            comment TEXT,
            exec TEXT,
            source TEXT,
            categories TEXT,
            tags TEXT,
            last_seen REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS docs (
            id TEXT PRIMARY KEY,
            title TEXT,
            tags TEXT,
            source TEXT,
            path TEXT,
            content_hash TEXT,
            added_at REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profile (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )


def _execute(query: str, params: tuple = ()) -> sqlite3.Cursor:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    return cur


def get_pref(key: str) -> Optional[str]:
    cur = get_connection().execute("SELECT value FROM prefs WHERE key=?", (key,))
    row = cur.fetchone()
    return row[0] if row else None


def set_pref(key: str, value: str) -> None:
    _execute(
        "INSERT INTO prefs(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_default(kind: str) -> Optional[str]:
    cur = get_connection().execute("SELECT target FROM defaults WHERE kind=?", (kind,))
    row = cur.fetchone()
    return row[0] if row else None


def set_default(kind: str, target: str) -> None:
    _execute(
        "INSERT INTO defaults(kind,target) VALUES(?,?) ON CONFLICT(kind) DO UPDATE SET target=excluded.target",
        (kind, target),
    )


def _safe_add_column(cur: sqlite3.Cursor, table: str, definition: str) -> None:
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")
    except sqlite3.OperationalError as exc:  # pragma: no cover - defensive
        if "duplicate column name" not in str(exc):
            raise


def _migrate_schema(cur: sqlite3.Cursor, current: int, target: int) -> None:
    if current < 2 <= target:
        _safe_add_column(cur, "aliases", "status TEXT DEFAULT 'provisional'")
        _safe_add_column(cur, "aliases", "success_count INTEGER DEFAULT 0")


def get_alias(phrase: str) -> Optional[Dict[str, object]]:
    cur = get_connection().execute(
        "SELECT phrase,target,confidence,status,success_count FROM aliases WHERE phrase=?", (phrase,)
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "phrase": row[0],
        "target": row[1],
        "confidence": row[2],
        "status": row[3],
        "success_count": row[4],
    }


def set_alias(
    phrase: str,
    target: str,
    confidence: float = 1.0,
    status: str = "provisional",
    success_count: int = 0,
) -> None:
    _execute(
        "INSERT INTO aliases(phrase,target,confidence,status,success_count,created_at) "
        "VALUES(?,?,?,?,?,strftime('%s','now')) "
        "ON CONFLICT(phrase) DO UPDATE SET "
        "target=excluded.target, confidence=excluded.confidence, status=excluded.status, "
        "success_count=excluded.success_count, created_at=excluded.created_at",
        (phrase, target, confidence, status, success_count),
    )


def increment_alias_success(phrase: str) -> Optional[Dict[str, object]]:
    conn = get_connection()
    cur = conn.execute("SELECT target,success_count,status FROM aliases WHERE phrase=?", (phrase,))
    row = cur.fetchone()
    if not row:
        return None
    target = row["target"]
    current_count = row["success_count"] or 0
    status = row["status"] or "provisional"
    new_count = current_count + 1
    new_status = "confirmed" if new_count >= 2 else status
    conn.execute(
        "UPDATE aliases SET success_count=?, status=? WHERE phrase=?",
        (new_count, new_status, phrase),
    )
    conn.commit()
    return {"phrase": phrase, "target": target, "success_count": new_count, "status": new_status}


def get_user_profile() -> Dict[str, str]:
    conn = get_connection()
    cur = conn.execute("SELECT key,value FROM user_profile")
    return {row["key"]: row["value"] for row in cur.fetchall()}


def set_user_profile_entry(key: str, value: str) -> None:
    _execute(
        "INSERT INTO user_profile(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def bulk_upsert_app_index(entries: Iterable[Dict[str, object]]) -> None:
    conn = get_connection()
    data = [
        (
            entry.get("id"),
            entry.get("name"),
            entry.get("generic"),
            entry.get("comment"),
            entry.get("exec"),
            entry.get("source"),
            entry.get("categories"),
            entry.get("tags"),
            entry.get("last_seen", time.time()),
        )
        for entry in entries
    ]
    if not data:
        return
    conn.executemany(
        """
        INSERT INTO app_index(id,name,generic,comment,exec,source,categories,tags,last_seen)
        VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            generic=excluded.generic,
            comment=excluded.comment,
            exec=excluded.exec,
            source=excluded.source,
            categories=excluded.categories,
            tags=excluded.tags,
            last_seen=excluded.last_seen
        """,
        data,
    )
    conn.commit()


def search_app_index_by_tag(tag: str, limit: int = 10) -> List[Dict[str, object]]:
    cur = get_connection().execute(
        "SELECT id,name,generic,comment,exec,source,tags FROM app_index WHERE tags LIKE ? ORDER BY last_seen DESC LIMIT ?",
        (f"%{tag}%", limit),
    )
    rows = cur.fetchall()
    return [dict(row) for row in rows]


def search_app_index_by_name(term: str, limit: int = 10) -> List[Dict[str, object]]:
    pattern = f"%{term}%"
    cur = get_connection().execute(
        "SELECT id,name,generic,comment,exec,source,tags FROM app_index WHERE name LIKE ? OR generic LIKE ? ORDER BY last_seen DESC LIMIT ?",
        (pattern, pattern, limit),
    )
    rows = cur.fetchall()
    return [dict(row) for row in rows]
