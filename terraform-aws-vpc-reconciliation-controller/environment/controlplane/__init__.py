"""Black-box VPC control-plane HTTP API.

Seeds observed cloud state from a directory of JSON files. Controllers may
only interact through HTTP; seed files are not part of the public contract.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


class ControlPlaneState:
    def __init__(self, seed_dir: Path) -> None:
        self.lock = threading.RLock()
        self.seed_dir = seed_dir
        self.reset()

    def reset(self) -> None:
        with self.lock:
            routes = _load(self.seed_dir / "routes.json")
            endpoints = _load(self.seed_dir / "endpoints.json")
            nat = _load(self.seed_dir / "nat_health.json")
            imports = _load(self.seed_dir / "imports.json")
            audit = _load(self.seed_dir / "audit.json")
            self.observed = {
                "route_tables": routes.get("route_tables", []),
                "endpoints": endpoints.get("endpoints", []),
                "nat_health": nat,
                "imports": imports,
                "audit": audit,
            }
            self.committed: dict[str, Any] = {
                "route_tables": [],
                "endpoints": [],
                "tokens": {},
            }
            self._idem: dict[str, dict[str, Any]] = {}

    def observed_payload(self) -> dict[str, Any]:
        with self.lock:
            return json.loads(json.dumps(self.observed))

    def committed_payload(self) -> dict[str, Any]:
        with self.lock:
            return json.loads(json.dumps(self.committed))

    def commit_routes(self, body: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            owner = str(body.get("owner") or "")
            digest = str(body.get("config_digest") or "")
            tables = body.get("route_tables")
            if not owner or not isinstance(tables, list):
                raise ValueError("owner and route_tables required")
            key = f"route:{owner}:{digest}:{_digest(tables)}"
            if key in self._idem:
                return self._idem[key]
            token = hashlib.sha256(f"route:{owner}:{digest}:{_digest(tables)}".encode()).hexdigest()[:24]
            self.committed["route_tables"] = tables
            self.committed["tokens"]["route"] = token
            # Reflect into observed so later GETs see committed reality.
            by_id = {str(t.get("id")): t for t in tables if isinstance(t, dict)}
            merged = []
            for obs in self.observed["route_tables"]:
                rid = str(obs.get("id"))
                merged.append(by_id.get(rid, obs))
            for rid, table in by_id.items():
                if rid not in {str(t.get("id")) for t in merged}:
                    merged.append(table)
            self.observed["route_tables"] = merged
            resp = {"accepted": True, "token": token, "stage": "route_commit"}
            self._idem[key] = resp
            return resp

    def commit_endpoints(self, body: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            owner = str(body.get("owner") or "")
            digest = str(body.get("config_digest") or "")
            endpoints = body.get("endpoints")
            if not owner or not isinstance(endpoints, list):
                raise ValueError("owner and endpoints required")
            key = f"endpoint:{owner}:{digest}:{_digest(endpoints)}"
            if key in self._idem:
                return self._idem[key]
            token = hashlib.sha256(
                f"endpoint:{owner}:{digest}:{_digest(endpoints)}".encode()
            ).hexdigest()[:24]
            self.committed["endpoints"] = endpoints
            self.committed["tokens"]["endpoint"] = token
            by_svc = {
                str(e.get("service")): e for e in endpoints if isinstance(e, dict)
            }
            merged = []
            for obs in self.observed["endpoints"]:
                svc = str(obs.get("service"))
                if svc in by_svc:
                    upd = dict(obs)
                    upd["route_table_ids"] = by_svc[svc].get("route_table_ids")
                    if "policy" in by_svc[svc]:
                        upd["policy"] = by_svc[svc]["policy"]
                    if "id" in by_svc[svc] and by_svc[svc]["id"]:
                        upd["id"] = by_svc[svc]["id"]
                    merged.append(upd)
                else:
                    merged.append(obs)
            for svc, ep in by_svc.items():
                if svc not in {str(e.get("service")) for e in merged}:
                    merged.append(ep)
            self.observed["endpoints"] = merged
            resp = {"accepted": True, "token": token, "stage": "endpoint_commit"}
            self._idem[key] = resp
            return resp


def make_handler(state: ControlPlaneState):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
            return

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")

        def _send(self, code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/health":
                self._send(200, {"ok": True})
                return
            if path == "/v1/observed":
                self._send(200, state.observed_payload())
                return
            if path == "/v1/committed":
                self._send(200, state.committed_payload())
                return
            self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                body = self._read_json()
                if path == "/v1/routes/commit":
                    self._send(200, state.commit_routes(body))
                    return
                if path == "/v1/endpoints/commit":
                    self._send(200, state.commit_endpoints(body))
                    return
                if path == "/v1/reset":
                    state.reset()
                    self._send(200, {"reset": True})
                    return
                self._send(404, {"error": "not found"})
            except Exception as exc:  # noqa: BLE001
                self._send(400, {"error": str(exc)})

    return Handler


def serve(seed_dir: Path, host: str, port: int) -> ThreadingHTTPServer:
    state = ControlPlaneState(seed_dir)
    server = ThreadingHTTPServer((host, port), make_handler(state))
    server.state = state  # type: ignore[attr-defined]
    return server


def main() -> int:
    seed = Path(os.environ.get("VPC_CP_SEED", "/app/seed"))
    host = os.environ.get("VPC_CP_HOST", "127.0.0.1")
    port = int(os.environ.get("VPC_CP_PORT", "7432"))
    server = serve(seed, host, port)
    print(json.dumps({"listening": f"http://{host}:{port}", "seed": str(seed)}))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
