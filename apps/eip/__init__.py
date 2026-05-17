"""Wake-on-LAN and hub status routes for EIP."""

from __future__ import annotations

from datetime import datetime, timezone
import os
import shlex
import socket
import subprocess

from flask import Blueprint, jsonify, render_template_string

bp = Blueprint("eip", __name__)

_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>EIP Control</title>
  <style>
    body { background: #111; color: #e5e7eb; font-family: system-ui, sans-serif; margin: 0; padding: 2rem; }
    main { max-width: 720px; }
    button { background: #e5e7eb; border: 0; border-radius: 4px; color: #111; cursor: pointer; padding: 0.6rem 1rem; }
    pre { background: #1f2937; border-radius: 6px; overflow: auto; padding: 1rem; white-space: pre-wrap; }
    a { color: #93c5fd; }
  </style>
</head>
<body>
  <main>
    <h1>Edge Infrastructure Platform</h1>
    <p>Private control plane for hub status and Wake-on-LAN.</p>
    <p><a href="{{ url_for('eip.hub_status') }}">Hub status JSON</a></p>
    <form method="post" action="{{ url_for('eip.wake') }}">
      <button type="submit">Wake Hub</button>
    </form>
    {% if output %}<pre>{{ output }}</pre>{% endif %}
  </main>
</body>
</html>
"""


def _hub_host() -> str:
    return os.environ.get("EIP_HUB_HOST", "hub.taildbe427.ts.net")


def _hub_port() -> int:
    return int(os.environ.get("EIP_HUB_PORT", "3389"))


def _status_timeout() -> float:
    return float(os.environ.get("EIP_STATUS_TIMEOUT", "2"))


def _wake_command() -> list[str]:
    command = os.environ.get("EIP_WAKE_COMMAND", "wakepc hub")
    return shlex.split(command)


def probe_tcp(host: str, port: int, timeout: float) -> bool:
    """Return True when a TCP connection can be established."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@bp.get("/")
def index():
    return render_template_string(_TEMPLATE, output=None)


@bp.get("/api/status/hub")
def hub_status():
    online = probe_tcp(_hub_host(), _hub_port(), _status_timeout())
    return jsonify(
        {
            "target": "hub",
            "host": _hub_host(),
            "port": _hub_port(),
            "status": "ONLINE" if online else "OFFLINE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@bp.post("/wake")
def wake():
    try:
        result = subprocess.run(
            _wake_command(),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip() or f"Wake command exited with {result.returncode}."
    except Exception as exc:  # command missing, timeout, or local execution failure
        output = str(exc)
    return render_template_string(_TEMPLATE, output=output)
