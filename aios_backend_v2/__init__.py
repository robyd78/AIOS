"""AIOS backend v2 package."""

from __future__ import annotations

import os

_TRUE_SET = {"1", "true", "on", "yes"}
_FALSE_SET = {"0", "false", "off", "no"}


def flag(name: str, default: bool = False) -> bool:
    """Read a boolean feature flag from the environment with sane defaults."""
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip().lower()
    if value in _TRUE_SET:
        return True
    if value in _FALSE_SET:
        return False
    return default


__all__ = ["flag"]
