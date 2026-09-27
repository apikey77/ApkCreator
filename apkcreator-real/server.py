#!/usr/bin/env python3
"""Flask API for creating Android WebView projects and optional APKs."""
from pathlib import Path
import threading
import uuid

from flask import Flask, jsonify, request, send_from_directory

from generator import BuildError, build_project

BASE = Path(__file__).resolve().parent
WORK = BASE / "builds"
WORK.mkdir(exist_ok=True)
app = Flask(__name__, static_folder=None)


def validate_payload(data):
    if not isinstance(data, dict):
        raise ValueError("JSON object required")
    url = str(data.get("url", "")).strip()
    html = str(data.get("html", "")).strip()
    if not url and not html:
        raise ValueError("Provide either a URL or HTML source")
    if url and not (url.startswith("https://") or url.startswith("http://")):
        raise ValueError("URL must start with http:// or https://")
    return {
        "name": str(data.get("name", "Web App")),
        "package": str(data.get("package", "com.example.webapp")),
        "version_code": int(data.get("version_code", 1)),
        "version_name": str(data.get("version_name", "1.0.0")),
        "url": url,
        "html": html,
        "allow_http": bool(data.get("allow_http", False)),
    }


@app.get("/")
def index():
    return send_from_directory(BASE, "index.html")


@app.post("/api/build")
def build():
    try:
        config = validate_payload(request.get_json(silent=True))
        build_id = uuid.uuid4().hex
        output = WORK / build_id
        result = build_project(config, output)
        return jsonify({"id": build_id, **result}), 201
    except (ValueError, BuildError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        app.logger.exception("build failed")
        return jsonify({"error": "internal build error"}), 500


@app.get("/api/build/<build_id>/download/<path:filename>")
def download(build_id, filename):
    directory = WORK / build_id
    return send_from_directory(directory, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
