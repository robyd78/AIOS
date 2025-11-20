from __future__ import annotations

import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

from .pkg_allowlist import get_package_id


def _sudo_prefix(cmd: List[str]) -> List[str]:
    return ["sudo"] + cmd


def build_install_command(canon: str, channel: str) -> Dict[str, Optional[List[str]]]:
    pkg = get_package_id(canon, channel)
    if not pkg:
        return {"dry_run": None, "apply": None}
    if channel == "apt":
        return {
            "dry_run": _sudo_prefix(["apt-get", "install", "-s", pkg]),
            "apply": _sudo_prefix(["apt-get", "install", "-y", pkg]),
        }
    if channel == "snap":
        return {
            "dry_run": None,
            "apply": _sudo_prefix(["snap", "install", pkg]),
        }
    if channel == "flatpak":
        return {
            "dry_run": None,
            "apply": ["flatpak", "install", "-y", "flathub", pkg],
        }
    return {"dry_run": None, "apply": None}


def build_remove_command(canon: str, channel: str) -> Dict[str, Optional[List[str]]]:
    pkg = get_package_id(canon, channel)
    if not pkg:
        return {"dry_run": None, "apply": None}
    if channel == "apt":
        return {
            "dry_run": _sudo_prefix(["apt-get", "remove", "-s", pkg]),
            "apply": _sudo_prefix(["apt-get", "remove", "-y", pkg]),
        }
    if channel == "snap":
        return {
            "dry_run": None,
            "apply": _sudo_prefix(["snap", "remove", pkg]),
        }
    if channel == "flatpak":
        return {
            "dry_run": None,
            "apply": ["flatpak", "uninstall", "-y", pkg],
        }
    return {"dry_run": None, "apply": None}


def build_update_command(canon: str, channel: str) -> Dict[str, Optional[List[str]]]:
    pkg = get_package_id(canon, channel)
    if not pkg:
        return {"dry_run": None, "apply": None}
    if channel == "apt":
        return {
            "dry_run": _sudo_prefix(["apt-get", "install", "-s", pkg]),
            "apply": _sudo_prefix(["apt-get", "install", "--only-upgrade", "-y", pkg]),
        }
    if channel == "snap":
        return {
            "dry_run": None,
            "apply": _sudo_prefix(["snap", "refresh", pkg]),
        }
    if channel == "flatpak":
        return {
            "dry_run": None,
            "apply": ["flatpak", "update", "-y", pkg],
        }
    return {"dry_run": None, "apply": None}


def run_command(cmd: List[str]) -> Tuple[int, str, str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
