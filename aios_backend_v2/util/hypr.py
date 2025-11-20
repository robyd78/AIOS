from __future__ import annotations

import json
import subprocess
from typing import List, Set, Union

from ..settings import WS_DIR


def _hypr_json(cmd: list[str]):
    out = subprocess.check_output(cmd)
    return json.loads(out)


def list_workspaces() -> list[dict]:
    return _hypr_json(["hyprctl", "workspaces", "-j"])


def list_clients() -> list[dict]:
    return _hypr_json(["hyprctl", "clients", "-j"])


def used_workspace_ids() -> Set[int]:
    return {w["id"] for w in list_workspaces()}


def pick_free_workspace(start: int = 2) -> int:
    used = used_workspace_ids()
    n = max(start, 1)
    while n in used:
        n += 1
    return n


def mark_aios_workspace(ws_id: int) -> None:
    (WS_DIR / f"aios-ws-{ws_id}").touch(exist_ok=True)


def unmark_aios_workspace(ws_id: int) -> None:
    p = WS_DIR / f"aios-ws-{ws_id}"
    if p.exists():
        p.unlink()


def listed_aios_workspaces() -> List[int]:
    out: List[int] = []
    for p in WS_DIR.glob("aios-ws-*"):
        try:
            out.append(int(p.name.split("-")[-1]))
        except Exception:
            pass
    return sorted(out)


def workspace_has_windows(ws_id: int) -> bool:
    for client in list_clients():
        ws = client.get("workspace") or {}
        if ws.get("id") == ws_id:
            return True
    return False


def switch_workspace(target: Union[int, str]) -> None:
    subprocess.Popen(
        ["hyprctl", "dispatch", "workspace", str(target)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
