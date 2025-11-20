from __future__ import annotations

from typing import Any, Dict

from .base import Tool
from ..util.pkg_allowlist import CHANNEL_ORDER, resolve_package, choose_channel, get_display_name
from ..util.pkg_commands import build_remove_command, run_command


class PkgRemove(Tool):
    name = "pkg_remove"
    description = "Remove an app/package from the trusted allowlist."
    permissions = ["pkg:remove"]
    params_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "channel": {"type": "string", "enum": CHANNEL_ORDER},
        },
        "required": ["name"],
        "additionalProperties": False,
    }
    returns_schema = {"type": "object"}

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        raw = (args.get("name") or "").strip()
        channel_hint = args.get("channel")
        canon = resolve_package(raw)
        if not canon:
            return {"ok": False, "error": f"'{raw}' not in removal allowlist"}
        channel = choose_channel(canon, channel_hint)
        if not channel:
            return {"ok": False, "error": "No supported channel"}
        commands = build_remove_command(canon, channel)
        apply_cmd = commands.get("apply")
        if not apply_cmd:
            return {"ok": False, "error": "Unable to build remove command"}
        dry_cmd = commands.get("dry_run")
        dry_result = {"stdout": "", "stderr": "", "returncode": None}
        if dry_cmd:
            rc, out, err = run_command(dry_cmd)
            dry_result = {"stdout": out, "stderr": err, "returncode": rc}
            if rc != 0:
                return {
                    "ok": False,
                    "channel": channel,
                    "name": canon,
                    "commands": {"dry_run": " ".join(dry_cmd), "apply": " ".join(apply_cmd)},
                    "dry_run": dry_result,
                    "error": "Dry-run failed; aborting remove",
                }
        rc, out, err = run_command(apply_cmd)
        note = f"Removed {get_display_name(canon)} via {channel}"
        return {
            "ok": rc == 0,
            "channel": channel,
            "name": canon,
            "commands": {"dry_run": " ".join(dry_cmd) if dry_cmd else None, "apply": " ".join(apply_cmd)},
            "dry_run": dry_result,
            "apply": {"stdout": out, "stderr": err, "returncode": rc},
            "note": note,
        }


tool = PkgRemove()
