"""Allowlisted operational actions for the EIP dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shlex
import subprocess


@dataclass(frozen=True)
class DashboardAction:
    """A named command the dashboard is allowed to run."""

    id: str
    label: str
    group: str
    command: list[str]
    mode: str = "run"
    timeout: float = 10
    available: bool = True
    unavailable_reason: str | None = None

    def public(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "group": self.group,
            "mode": self.mode,
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
        }


def wake_command() -> list[str]:
    command = os.environ.get("EIP_WAKE_COMMAND", "wakepc hub")
    return shlex.split(command)


def _expanded_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value)))


def _script_path(env_name: str, default_name: str) -> Path:
    default_path = Path.home() / "Scripts" / default_name
    return _expanded_path(os.environ.get(env_name, str(default_path)))


def _windows_launch_command(*args: str) -> list[str]:
    return ["cmd.exe", "/c", "start", "", *args]


def _script_action(
    action_id: str,
    label: str,
    env_name: str,
    default_name: str,
) -> DashboardAction:
    path = _script_path(env_name, default_name)
    available = os.name == "nt" and path.exists()
    reason = None
    if os.name != "nt":
        reason = "Only available on Windows."
    elif not path.exists():
        reason = f"Script not found: {path}"

    return DashboardAction(
        id=action_id,
        label=label,
        group="Laptop",
        command=_windows_launch_command(str(path)),
        mode="launch",
        available=available,
        unavailable_reason=reason,
    )


def configured_actions() -> list[DashboardAction]:
    hub_host = os.environ.get("EIP_RDP_HOST", os.environ.get("EIP_HUB_HOST", "hub"))
    rdp_available = os.name == "nt"
    return [
        DashboardAction(
            id="wake-hub",
            label="Wake Hub",
            group="Hub",
            command=wake_command(),
            mode="run",
            timeout=10,
        ),
        DashboardAction(
            id="open-rdp",
            label="Open RDP",
            group="Hub",
            command=_windows_launch_command("mstsc.exe", f"/v:{hub_host}"),
            mode="launch",
            available=rdp_available,
            unavailable_reason=None if rdp_available else "Only available on Windows.",
        ),
        _script_action(
            "wake-and-rdp",
            "Wake + RDP Script",
            "EIP_WAKE_RDP_SCRIPT",
            "wake_and_rdp.bat",
        ),
        _script_action(
            "wake-and-backup",
            "Wake + Backup Script",
            "EIP_WAKE_BACKUP_SCRIPT",
            "wake_and_backup.bat",
        ),
    ]


def find_action(action_id: str) -> DashboardAction | None:
    return next((action for action in configured_actions() if action.id == action_id), None)


def run_action(action: DashboardAction) -> dict:
    if not action.available:
        return {
            "ok": False,
            "action": action.public(),
            "output": action.unavailable_reason or "Action unavailable.",
            "returncode": None,
        }

    try:
        if action.mode == "launch":
            process = subprocess.Popen(action.command)
            return {
                "ok": True,
                "action": action.public(),
                "output": f"Launched {action.label}.",
                "returncode": None,
                "pid": process.pid,
            }

        result = subprocess.run(
            action.command,
            capture_output=True,
            text=True,
            timeout=action.timeout,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip() or f"{action.label} exited with {result.returncode}."
        return {
            "ok": result.returncode == 0,
            "action": action.public(),
            "output": output,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "action": action.public(),
            "output": f"{action.label} timed out after {action.timeout:g}s.",
            "returncode": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "action": action.public(),
            "output": str(exc),
            "returncode": None,
        }
