"""Edge Infrastructure Platform Flask entry point.

The platform owns process boot, env loading, app registration, and health.
Operational features live in app modules.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os

from flask import Flask, jsonify

from apps.eip import bp as eip_bp


def load_env(path: str | os.PathLike | None = None) -> None:
    """Load simple KEY=VALUE pairs from .env without overriding environment."""
    env_path = Path(path) if path else Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def create_app() -> Flask:
    load_env()
    app = Flask(__name__)
    app.register_blueprint(eip_bp, url_prefix="/eip")

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "apps": {"eip": "/eip"},
            }
        )

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def server_error(_error):
        return jsonify({"error": "internal server error"}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    host = os.environ.get("EIP_HOST", "0.0.0.0")
    port = int(os.environ.get("EIP_PORT", "5000"))
    debug = os.environ.get("EIP_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
