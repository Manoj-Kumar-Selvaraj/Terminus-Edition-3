"""HTTP frontend for the SQLite Terraform state backend."""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .clock import Clock
from .store import Store, StoreError

WS_STATE = re.compile(r"^/v1/workspaces/([^/]+)/state$")
WS_LOCK = re.compile(r"^/v1/workspaces/([^/]+)/lock$")


def _json_body(handler: BaseHTTPRequestHandler) -> Any:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b""
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _raw_body(handler: BaseHTTPRequestHandler) -> str:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b""
    return raw.decode("utf-8")


def make_handler(store: Store) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
            return

        def _send(self, status: int, payload: Any | None = None, raw: bytes | None = None) -> None:
            if raw is not None:
                body = raw
                content_type = "application/json"
            elif payload is None:
                body = b""
                content_type = "application/json"
            else:
                body = json.dumps(payload, sort_keys=True).encode("utf-8")
                content_type = "application/json"
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/v1/control/health":
                self._send(200, {"ok": True})
                return
            if path == "/v1/control/clock":
                self._send(200, {"tick": store.clock.now()})
                return
            match = WS_STATE.match(path)
            if match:
                body, _md5 = store.get_state(match.group(1))
                if body is None:
                    self._send(404, {"error": "empty state"})
                    return
                self._send(200, raw=body.encode("utf-8"))
                return
            self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            query = parse_qs(urlparse(self.path).query)
            if path == "/v1/control/advance":
                try:
                    payload = _json_body(self)
                    tick = store.clock.advance(int(payload.get("ticks", 0)))
                    self._send(200, {"tick": tick})
                except Exception as exc:  # noqa: BLE001
                    self._send(400, {"error": str(exc)})
                return
            match = WS_STATE.match(path)
            if match:
                workspace = match.group(1)
                body = _raw_body(self)
                lock_id = (
                    self.headers.get("Lock-ID")
                    or self.headers.get("lock-id")
                    or self.headers.get("X-Terraform-Lock-ID")
                )
                if not lock_id:
                    ids = query.get("ID") or query.get("id")
                    if ids:
                        lock_id = ids[0]
                idem = self.headers.get("Idempotency-Key") or self.headers.get(
                    "idempotency-key"
                )
                try:
                    result = store.put_state(workspace, body, lock_id, idem)
                    self._send(200, result)
                except StoreError as exc:
                    self._send(exc.status, {"error": exc.message})
                except Exception as exc:  # noqa: BLE001
                    self._send(500, {"error": str(exc)})
                return
            self._send(404, {"error": "not found"})

        def do_LOCK(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            match = WS_LOCK.match(path)
            if not match:
                self._send(404, {"error": "not found"})
                return
            try:
                info = _json_body(self)
                result = store.lock(match.group(1), info)
                self._send(200, result)
            except StoreError as exc:
                self._send(exc.status, {"error": exc.message})
            except Exception as exc:  # noqa: BLE001
                self._send(500, {"error": str(exc)})

        def do_UNLOCK(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            match = WS_LOCK.match(path)
            if not match:
                self._send(404, {"error": "not found"})
                return
            try:
                info = _json_body(self)
                store.unlock(match.group(1), info)
                self._send(200, {"status": "unlocked"})
            except StoreError as exc:
                self._send(exc.status, {"error": exc.message})
            except Exception as exc:  # noqa: BLE001
                self._send(500, {"error": str(exc)})

    return Handler


def serve(
    host: str = "127.0.0.1",
    port: int = 18765,
    data_dir: Path | None = None,
    lease_ttl_ticks: int | None = None,
) -> ThreadingHTTPServer:
    data = Path(data_dir or os.environ.get("BACKEND_DATA_DIR", "/app/var/backend-store"))
    ttl = int(
        lease_ttl_ticks
        if lease_ttl_ticks is not None
        else os.environ.get("LEASE_TTL_TICKS", "10")
    )
    clock = Clock()
    store = Store(data / "state.db", clock, lease_ttl_ticks=ttl)
    handler = make_handler(store)
    server = ThreadingHTTPServer((host, port), handler)
    server.store = store  # type: ignore[attr-defined]
    return server


def main() -> None:
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("BACKEND_PORT", "18765"))
    server = serve(host=host, port=port)
    ready = Path(os.environ.get("BACKEND_READY_FILE", "/app/var/backend-store/ready"))
    ready.parent.mkdir(parents=True, exist_ok=True)
    ready.write_text(f"{host}:{port}\n", encoding="utf-8")
    try:
        server.serve_forever()
    finally:
        server.store.close()  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
