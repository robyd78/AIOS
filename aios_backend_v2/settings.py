from __future__ import annotations

import os
from pathlib import Path

from . import flag


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "var" / "aios"
DATA_DIR = Path(os.getenv("AIOS_DATA_DIR", str(DEFAULT_DATA_DIR))).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)

LTM_DIR = Path(os.getenv("AIOS_LTM_STORE", str(DATA_DIR / "ltm"))).expanduser()
LTM_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = Path(os.getenv("AIOS_LOG_DIR", str(DATA_DIR / "logs"))).expanduser()
LOG_DIR.mkdir(parents=True, exist_ok=True)
PROMPT_DUMP_DIR = LOG_DIR / "prompt_dump"
PROMPT_DUMP_DIR.mkdir(parents=True, exist_ok=True)

WS_DIR = Path(os.getenv("AIOS_WS_DIR", str(DATA_DIR / "ws"))).expanduser()
WS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.getenv("AIOS_DB_PATH", str(DATA_DIR / "aios.db"))).expanduser()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DEBUG_CONTEXT = flag("AIOS_DEBUG_CONTEXT")
DEBUG_PROMPT_DUMP = flag("AIOS_DEBUG_PROMPT_DUMP")

__all__ = [
    "DEBUG_CONTEXT",
    "DEBUG_PROMPT_DUMP",
    "DATA_DIR",
    "LTM_DIR",
    "LOG_DIR",
    "PROMPT_DUMP_DIR",
    "WS_DIR",
    "DB_PATH",
]
