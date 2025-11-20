from __future__ import annotations

import importlib
import os
from typing import Any, Dict, List

from .base import Tool, serialize_tool

PKG_TOOLS_ENABLED = os.getenv("AIOS_PKG_TOOLS", "off").lower() in {"1", "true", "on"}
PKG_MUTATIONS_ENABLED = os.getenv("AIOS_PKG_MUTATIONS_V1", "off").lower() in {"1", "true", "on"}

TOOLS_PACKAGES = [
    "aios_backend_v2.tools.impl_datetime",
    "aios_backend_v2.tools.impl_open_app",
    "aios_backend_v2.tools.impl_open_terminal",
    "aios_backend_v2.tools.impl_close_aios_workspaces",
    "aios_backend_v2.tools.impl_resolve_app_debug",
    "aios_backend_v2.tools.impl_session_plan",
    "aios_backend_v2.tools.impl.mkdir",
    "aios_backend_v2.tools.impl.touch",
    "aios_backend_v2.tools.impl.run_cmd_safe",
    "aios_backend_v2.tools.impl.run_cmd_risky",
]

if PKG_TOOLS_ENABLED:
    TOOLS_PACKAGES += [
        "aios_backend_v2.tools.impl_pkg_search",
        "aios_backend_v2.tools.impl_pkg_info",
        "aios_backend_v2.tools.impl_pkg_plan_install",
    ]

if PKG_TOOLS_ENABLED and PKG_MUTATIONS_ENABLED:
    TOOLS_PACKAGES += [
        "aios_backend_v2.tools.impl_pkg_install",
        "aios_backend_v2.tools.impl_pkg_remove",
        "aios_backend_v2.tools.impl_pkg_update",
    "aios_backend_v2.tools.impl_system_refresh",
    ]

_registry: Dict[str, Tool] = {}
import os
_registry: Dict[str, Tool] = {}
TOOLS_PACKAGES += [
    "aios_backend_v2.tools.impl_user_profile",
    "aios_backend_v2.tools.impl_prompt_dump",
]
if os.getenv("AIOS_MEMORY_LTM_V1","off").lower() in {"1","true","on"}:
    TOOLS_PACKAGES += ["aios_backend_v2.tools.impl_memory_ltm"]



def load_tools() -> Dict[str, Tool]:
    global _registry
    if _registry:
        return _registry
    for modname in TOOLS_PACKAGES:
        module = importlib.import_module(modname)
        tools = []
        if hasattr(module, "tools"):
            tools = getattr(module, "tools")
        elif hasattr(module, "tool"):
            tools = [getattr(module, "tool")]
        else:
            raise RuntimeError(f"Tool module {modname} has no tool(s)")
        for tool in tools:
            _registry[tool.name] = tool
    return _registry


def list_tools() -> List[Dict[str, Any]]:
    return [serialize_tool(tool) for tool in load_tools().values()]


async def execute(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    tool = load_tools().get(name)
    if not tool:
        raise KeyError(f"unknown tool: {name}")
    return await tool.run(args or {})
