from __future__ import annotations

import re
from typing import Dict, Optional, Tuple


def infer_tool_call(intent: Dict, pkg_tools_enabled: bool = False) -> Tuple[Optional[Dict], float]:
    verb = intent.get("verb")
    mods = intent.get("modifiers", {})
    obj = intent.get("object", {})
    channel = intent.get("channel")

    def confidence(val: float) -> float:
        return max(0.0, min(1.0, val))

    if verb == "open_app":
        app = obj.get("canonical_app")
        conf = confidence(obj.get("confidence", 0.0))
        if app and conf >= 0.6:
            args: Dict[str, object] = {"app": app}
            if mods.get("fullscreen"):
                args["fullscreen"] = True
            if mods.get("workspace"):
                args["aios_workspace"] = "none"  # explicit workspace; user will steer
                args["workspace"] = mods.get("workspace")
            if channel:
                args["channel"] = channel
            return ({"name": "open_app", "arguments": args}, conf)

    if verb == "run" and obj.get("tui"):
        args: Dict[str, object] = {"program": obj["tui"]}
        if mods.get("terminal"):
            args["terminal"] = mods["terminal"]
        return ({"name": "open_terminal", "arguments": args}, 0.95)

    if verb == "profile_set":
        profile = obj.get("profile_update") or {}
        key = profile.get("key")
        value = profile.get("value")
        if key and value:
            return ({"name": "user_profile.set", "arguments": {"key": key, "value": value}}, 0.95)

    ltm_command = obj.get("ltm_command") or {}
    action = ltm_command.get("action")
    if action == "add" and obj.get("ltm_command"):
        text = ltm_command.get("text")
        if text:
            return ({"name": "memory_ltm_add", "arguments": {"text": text}}, 0.95)
    if action == "search":
        query = ltm_command.get("query")
        if query:
            return ({"name": "memory_ltm_search", "arguments": {"query": query}}, 0.95)
    if action == "forget":
        target = ltm_command.get("target") or ""
        target = target.strip()
        if target:
            if re.match(r"[0-9a-fA-F-]{36}", target):
                return ({"name": "memory_ltm_forget", "arguments": {"id": target.split()[0]}}, 0.95)
            return ({"name": "memory_ltm_search", "arguments": {"query": target}}, 0.7)

    return (None, 0.0)
