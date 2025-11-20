import json
import os
import pathlib
from typing import Dict

PERMS_PATH = os.path.expanduser("~/.config/aios/permissions.json")


def _ensure_dirs() -> None:
    pathlib.Path(os.path.dirname(PERMS_PATH)).mkdir(parents=True, exist_ok=True)


def load_perms() -> Dict[str, bool]:
    _ensure_dirs()
    if not os.path.exists(PERMS_PATH):
        return {}
    try:
        with open(PERMS_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_perms(perms: Dict[str, bool]) -> None:
    _ensure_dirs()
    with open(PERMS_PATH, "w", encoding="utf-8") as fh:
        json.dump(perms, fh, indent=2)


def is_allowed(permission: str) -> bool:
    return load_perms().get(permission, False)


def set_permission(permission: str, value: bool) -> Dict[str, bool]:
    perms = load_perms()
    perms[permission] = value
    save_perms(perms)
    return perms


def list_permissions() -> Dict[str, bool]:
    return load_perms()
