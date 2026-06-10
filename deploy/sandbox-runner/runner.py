#!/usr/bin/env python3
"""Minimal sandbox-runner sidecar: POST /execute runs isolated Python subprocess."""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

MAX_STDOUT = 65536
MAX_TIMEOUT_SEC = 30
PORT = 8091


class ExecuteHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/execute":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid_json"})
            return

        code = str(body.get("code", ""))
        timeout_sec = min(int(body.get("timeout_sec", 5)), MAX_TIMEOUT_SEC)
        if not code.strip():
            self._json(400, {"error": "empty_code"})
            return

        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            self._json(
                200,
                {
                    "stdout": (proc.stdout or "")[:MAX_STDOUT],
                    "stderr": (proc.stderr or "")[:MAX_STDOUT],
                    "exit_code": proc.returncode,
                },
            )
        except subprocess.TimeoutExpired:
            self._json(408, {"error": "timeout"})
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    server = HTTPServer(("0.0.0.0", PORT), ExecuteHandler)
    print(f"sandbox-runner listening on :{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
