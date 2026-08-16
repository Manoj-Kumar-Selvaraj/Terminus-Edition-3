"""Socket server for the control-plane HTTP surface.

The server does nothing but translate between HTTP framing and
:func:`cc.api.app.handle`, so both operator surfaces share one implementation.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from cc.api.app import handle

MAX_BODY = 1 << 20


class ControlPlaneHandler(BaseHTTPRequestHandler):
    """Adapter between BaseHTTPRequestHandler and the router."""

    server_version = "codecommit-control-plane"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _read_body(self) -> Any:
        raw_length = self.headers.get("Content-Length")
        if not raw_length:
            return None
        try:
            length = int(raw_length)
        except ValueError:
            return None
        if length <= 0:
            return None
        if length > MAX_BODY:
            return None
        payload = self.rfile.read(length)
        if not payload:
            return None
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"__invalid_json__": True}

    def _respond(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve(self, method: str) -> None:
        headers = {key.lower(): value for key, value in self.headers.items()}
        body = self._read_body() if method in {"POST", "PUT", "PATCH"} else None
        status, payload = handle(method, self.path, headers, body)
        self._respond(status, payload)

    def do_GET(self) -> None:  # noqa: N802 - required handler name
        self._serve("GET")

    def do_POST(self) -> None:  # noqa: N802 - required handler name
        self._serve("POST")


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Start the control-plane API and announce the bound port on stdout."""
    httpd = ThreadingHTTPServer((host, port), ControlPlaneHandler)
    bound = httpd.server_address[1]
    sys.stdout.write(json.dumps({"ok": True, "host": host, "port": bound}) + "\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
