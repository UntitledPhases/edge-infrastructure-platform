"""Wake-on-LAN, hub status, and operator dashboard routes for EIP."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import os
import socket

from flask import Blueprint, jsonify, render_template

from .actions import configured_actions, find_action, run_action

bp = Blueprint("eip", __name__, template_folder="templates")


def _hub_host() -> str:
    return os.environ.get("EIP_HUB_HOST", "hub.tailnet.example")


def _hub_port() -> int:
    return int(os.environ.get("EIP_HUB_PORT", "3389"))


def _status_timeout() -> float:
    return float(os.environ.get("EIP_STATUS_TIMEOUT", "2"))


def probe_tcp(host: str, port: int, timeout: float) -> bool:
    """Return True when a TCP connection can be established."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def hub_status_payload() -> dict:
    online = probe_tcp(_hub_host(), _hub_port(), _status_timeout())
    return {
        "target": "hub",
        "host": _hub_host(),
        "port": _hub_port(),
        "status": "ONLINE" if online else "OFFLINE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _actions_by_group() -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for action in configured_actions():
        groups[action.group].append(action.public())
    return dict(groups)


@bp.get("/")
def index():
    return render_template(
        "eip/dashboard.html",
        actions_by_group=_actions_by_group(),
        status=hub_status_payload(),
        output=None,
    )


@bp.get("/api/status/hub")
def hub_status():
    return jsonify(hub_status_payload())


@bp.get("/api/actions")
def actions():
    return jsonify({"actions": [action.public() for action in configured_actions()]})


@bp.post("/api/actions/<action_id>")
def action(action_id: str):
    selected = find_action(action_id)
    if selected is None:
        return jsonify({"error": "unknown action"}), 404
    status_code = 200 if selected.available else 409
    return jsonify(run_action(selected)), status_code


@bp.post("/wake")
def wake():
    selected = find_action("wake-hub")
    result = run_action(selected)
    return render_template(
        "eip/dashboard.html",
        actions_by_group=_actions_by_group(),
        status=hub_status_payload(),
        output=result["output"],
    )
