"""Live outbox server fixtures for behavioral verifier tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import subprocess
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import requests

APP = Path(os.environ.get("OUTBOX_ROOT", "/app/outbox"))
BINARY = APP / "bin" / "outboxd"
CTL_BINARY = APP / "bin" / "outboxctl"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _go_build(env: dict[str, str], package: str, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["go", "build", "-o", str(out), package],
        cwd=APP,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


@pytest.fixture(scope="session")
def built_binary() -> Path:
    """Rebuild the submitted outboxd and outboxctl binaries once per verifier session."""
    assert APP.is_dir(), f"missing artifact tree {APP}"
    env = os.environ.copy()
    env.setdefault("GOPROXY", "https://proxy.golang.org,direct")
    (APP / "bin").mkdir(parents=True, exist_ok=True)
    tidy = subprocess.run(
        ["go", "mod", "tidy"],
        cwd=APP,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    build = _go_build(env, "./cmd/outboxd", BINARY)
    if build.returncode != 0:
        pytest.fail(
            "go build outboxd failed\n"
            + tidy.stdout
            + tidy.stderr
            + build.stdout
            + build.stderr
        )
    ctl = _go_build(env, "./cmd/outboxctl", CTL_BINARY)
    if ctl.returncode != 0:
        pytest.fail(
            "go build outboxctl failed\n" + ctl.stdout + ctl.stderr
        )
    assert BINARY.is_file()
    assert CTL_BINARY.is_file()
    BINARY.chmod(0o755)
    CTL_BINARY.chmod(0o755)
    return BINARY


@pytest.fixture(scope="session")
def built_ctl(built_binary: Path) -> Path:
    """Return the rebuilt outboxctl binary path."""
    assert CTL_BINARY.is_file()
    return CTL_BINARY

class _SinkHandler(BaseHTTPRequestHandler):
    captures: list[dict]

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.captures.append(
            {
                "path": self.path,
                "headers": {k: v for k, v in self.headers.items()},
                "body": body,
            }
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


@pytest.fixture()
def http_sink() -> Iterator[dict]:
    """Local HTTP sink that records signed webhook deliveries."""
    captures: list[dict] = []

    class Handler(_SinkHandler):
        pass

    Handler.captures = captures
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield {"url": f"http://127.0.0.1:{port}/hook", "captures": captures, "port": port}
    server.shutdown()


@pytest.fixture()
def outbox(built_binary: Path, tmp_path: Path, http_sink: dict) -> Iterator[dict]:
    """Start an isolated outboxd against a temp DB with operator token set."""
    db = tmp_path / "outbox.db"
    data = tmp_path / "data"
    data.mkdir()
    port = _free_port()
    addr = f"127.0.0.1:{port}"
    token = "operator-secret-token"
    env = os.environ.copy()
    env.update(
        {
            "OUTBOX_ROOT": str(APP),
            "OUTBOX_DB": str(db),
            "OUTBOX_ADDR": addr,
            "OUTBOX_DATA": str(data),
            "OUTBOX_SYNC": "1",
            "OUTBOX_TOKEN": token,
        }
    )
    log_path = tmp_path / "outbox-server.log"
    log_fh = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [str(built_binary)],
        cwd=str(APP),
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://{addr}"
    deadline = time.monotonic() + 30
    last_err = ""
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            log_fh.flush()
            pytest.fail(f"outboxd exited early: {read_text(log_path)}")
        try:
            r = requests.get(f"{base}/api/v1/health", timeout=0.5)
            if r.status_code == 200 and r.json().get("status") == "ok":
                break
        except requests.RequestException as exc:
            last_err = str(exc)
            time.sleep(0.1)
    else:
        proc.kill()
        log_fh.flush()
        pytest.fail(f"outboxd did not become healthy: {last_err}\n{read_text(log_path)}")

    session = requests.Session()

    def api(method: str, path: str, **kwargs):
        kwargs.setdefault("timeout", 30)
        return session.request(method, base + path, **kwargs)

    yield {
        "base": base,
        "api": api,
        "db": db,
        "token": token,
        "sink": http_sink,
        "proc": proc,
        "log": log_path,
    }
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    log_fh.close()


def canonical(event_id: str, ts: str, body: bytes) -> bytes:
    return event_id.encode() + b"\n" + ts.encode() + b"\n" + body


def expect_signature(secret: str, event_id: str, ts: str, body: bytes) -> str:
    return hmac.new(secret.encode(), canonical(event_id, ts, body), hashlib.sha256).hexdigest()


def create_tenant(api, slug: str, quota: int = 1000) -> dict:
    r = api(
        "POST",
        "/api/v1/tenants",
        json={"name": slug.title(), "slug": slug, "deliveries_per_hour": quota},
    )
    assert r.status_code == 201, r.text
    return r.json()


def create_endpoint(api, tenant_id: str, url: str, secret: str = "hook-secret", max_attempts: int = 5) -> dict:
    r = api(
        "POST",
        f"/api/v1/tenants/{tenant_id}/endpoints",
        json={
            "name": "primary",
            "url": url,
            "hmac_secret": secret,
            "enabled": True,
            "max_attempts": max_attempts,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def enqueue(api, endpoint_id: str, payload: dict, idem: str | None = None) -> tuple[dict, int]:
    body: dict = {"payload": payload}
    if idem is not None:
        body["idempotency_key"] = idem
    r = api("POST", f"/api/v1/endpoints/{endpoint_id}/events", json=body)
    return r.json(), r.status_code
