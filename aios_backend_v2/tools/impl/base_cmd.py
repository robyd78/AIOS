from __future__ import annotations

import asyncio
import shlex
from typing import Dict, Any, List

def sanitize_command(cmd: List[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)

async def run_command(cmd: List[str]) -> Dict[str, Any]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return {
        "ok": proc.returncode == 0,
        "stdout": stdout.decode("utf-8", errors="ignore"),
        "stderr": stderr.decode("utf-8", errors="ignore"),
        "command": sanitize_command(cmd),
        "returncode": proc.returncode,
    }
