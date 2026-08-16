"""Live Stackyard server fixtures for behavioral verifier tests."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import requests

APP = Path(os.environ.get("STACKYARD_ROOT", "/app/stackyard"))
BINARY = APP / "bin" / "stackyard"
SHIM = APP / "bin" / "terraform-shim"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def built_binary() -> Path:
    """Rebuild the submitted Stackyard binary once per verifier session."""
    assert APP.is_dir(), f"missing artifact tree {APP}"
    assert SHIM.is_file(), "terraform-shim missing"
    SHIM.chmod(0o755)
    env = os.environ.copy()
    env.setdefault("GOPROXY", "https://proxy.golang.org,direct")
    tidy = subprocess.run(
        ["go", "mod", "tidy"],
        cwd=APP,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    build = subprocess.run(
        ["go", "build", "-o", str(BINARY), "./cmd/stackyard"],
        cwd=APP,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if build.returncode != 0:
        pytest.fail(
            "go build failed\n"
            + tidy.stdout
            + tidy.stderr
            + build.stdout
            + build.stderr
        )
    assert BINARY.is_file()
    BINARY.chmod(0o755)
    return BINARY


@pytest.fixture()
def stackyard(built_binary: Path, tmp_path: Path) -> Iterator[dict[str, object]]:
    """Start an isolated Stackyard server against a temp DB and shim log dir."""
    db = tmp_path / "stackyard.db"
    data = tmp_path / "workspaces"
    shim_dir = tmp_path / "shim"
    data.mkdir()
    shim_dir.mkdir()
    port = _free_port()
    addr = f"127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        {
            "STACKYARD_ROOT": str(APP),
            "STACKYARD_DB": str(db),
            "STACKYARD_ADDR": addr,
            "STACKYARD_DATA": str(data),
            "TERRAFORM_BIN": str(SHIM),
            "STACKYARD_SYNC": "1",
            "STACKYARD_SHIM_LOG_DIR": str(shim_dir),
            "STACKYARD_SHIM_LOG": str(shim_dir / "terraform-shim.log"),
            "STACKYARD_SHIM_ENV": str(shim_dir / "terraform-shim.env"),
            "STACKYARD_TOKEN": "",
        }
    )
    log_path = tmp_path / "stackyard-server.log"
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
            pytest.fail(f"stackyard exited early: {read_text(log_path)}")
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
        pytest.fail(f"stackyard did not become healthy: {last_err}\n{read_text(log_path)}")

    session = requests.Session()

    def api(method: str, path: str, **kwargs):
        kwargs.setdefault("timeout", 30)
        return session.request(method, base + path, **kwargs)

    yield {
        "base": base,
        "api": api,
        "db": db,
        "data": data,
        "shim_dir": shim_dir,
        "shim_log": shim_dir / "terraform-shim.log",
        "shim_env": shim_dir / "terraform-shim.env",
        "proc": proc,
    }
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    log_fh.close()


@pytest.fixture()
def acme_org(stackyard: dict[str, object]) -> dict:
    """Return the seeded acme organization."""
    api = stackyard["api"]
    r = api("GET", "/api/v1/orgs")
    assert r.status_code == 200
    orgs = r.json()["orgs"]
    acme = next(o for o in orgs if o["slug"] == "acme")
    return acme


@pytest.fixture()
def workspace(stackyard: dict[str, object], acme_org: dict) -> dict:
    """Create a fresh workspace under acme for each test."""
    api = stackyard["api"]
    name = f"ws-{time.time_ns()}"
    r = api(
        "POST",
        f"/api/v1/orgs/{acme_org['id']}/workspaces",
        json={"name": name, "working_directory": "infra"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
