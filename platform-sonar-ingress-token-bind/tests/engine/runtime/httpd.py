from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from . import paths
from .state import load_json

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8443


def _live() -> dict[str, Any]:
    return load_json(paths.live_path())


def _host_state(live: dict[str, Any], host: str) -> dict[str, Any] | None:
    for item in (live.get("hosts") or {}).values():
        if item.get("host") == host:
            return item
    return None


class PlatformHandler(BaseHTTPRequestHandler):
    server_version = "platform-ingress/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _write(self, code: int, body: bytes, content_type: str = "text/plain") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        live = _live()
        parsed = urlparse(self.path)
        host = (self.headers.get("Host") or "").split(":")[0]
        if parsed.path == "/__live":
            payload = json.dumps(live, sort_keys=True).encode("utf-8")
            self._write(200, payload, "application/json")
            return

        state = _host_state(live, host)
        if state is None or not live.get("listener_ok") and state and state.get("group") != "platform-ingress":
            # host not on the shared listener
            if state is None:
                self._write(404, b"no host\n")
                return
        if state is None:
            self._write(404, b"no host\n")
            return
        if not state.get("healthy") or state.get("group") != "platform-ingress":
            self._write(503, b"unhealthy target\n")
            return
        if not live.get("listener_ok") and state.get("group") != "platform-ingress":
            self._write(503, b"split listener\n")
            return

        if host == "jenkins.platform.test":
            if parsed.path == "/login":
                self._write(200, b"jenkins-login\n")
                return
            if parsed.path == "/credentials":
                payload = {
                    "id": live.get("credential_id"),
                    "token_present": bool(live.get("bound_token")),
                }
                self._write(200, json.dumps(payload).encode("utf-8"), "application/json")
                return
            self._write(404, b"jenkins\n")
            return

        if host == "sonar.platform.test":
            if parsed.path == "/api/system/status":
                status = "UP" if live.get("sonar_up") else "DOWN"
                payload = {"status": status}
                self._write(200, json.dumps(payload).encode("utf-8"), "application/json")
                return
            if parsed.path == "/api/authentication/validate":
                header = self.headers.get("Authorization") or ""
                token = ""
                if header.startswith("Bearer "):
                    token = header[7:]
                ok = bool(live.get("bound_token")) and token == live.get("bound_token")
                self._write(200, json.dumps({"valid": ok}).encode("utf-8"), "application/json")
                return
            self._write(404, b"sonar\n")
            return

        if host == "artifactory.platform.test":
            if parsed.path == "/artifactory/api/system/ping":
                self._write(200, b"OK\n")
                return
            self._write(404, b"artifactory\n")
            return

        self._write(404, b"unknown host\n")


def serve(host: str = LISTEN_HOST, port: int = LISTEN_PORT) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), PlatformHandler)
    return server
