"""Shared fixtures for the enterprise PII discovery plane verifier."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
import requests

PII_HOME = Path(os.environ.get("PII_HOME", "/app/enterprise-pii"))
FIXTURES = Path(os.environ.get("PII_TEST_FIXTURES", "/tests/fixtures"))
BUILD = PII_HOME / "scripts" / "build.sh"
CONTROL = PII_HOME / "bin" / "pii-control"
PIICTL = PII_HOME / "bin" / "piictl"
WORKER = PII_HOME / "bin" / "pii-worker"
GENERATE = PII_HOME / "bin" / "generate-corpus"
TENANT = "synthetic-enterprise"
FINGERPRINT_KEY = "c3ludGhldGljLW9mZmxpbmUtd29ya2VyLWtleS0wMDAwMQ=="

RAW_PII_PATTERNS = (
    r"\b\d{3}-\d{2}-\d{4}\b",
    r"\b4111\s*1111\s*1111\s*1111\b",
    r"synthetic\.[0-9]{6}@example\.invalid",
    r"\+1\s*202\s*555\s*[0-9]{4}",
)


def fixture_path(*parts: str) -> Path:
    """Return an absolute path under the hidden verifier fixtures tree."""
    return FIXTURES.joinpath(*parts)


def load_principals() -> dict[str, dict[str, Any]]:
    """Load authorization principals used by hidden verifier cases."""
    return json.loads(fixture_path("principals.json").read_text(encoding="utf-8"))


def principal_header(name: str) -> dict[str, str]:
    """Encode a fixture principal for the optional report authorization header."""
    body = json.dumps(load_principals()[name], separators=(",", ":")).encode()
    return {"X-PII-Principal": base64.b64encode(body).decode("ascii")}


def free_port() -> int:
    """Bind an ephemeral localhost port for an isolated control-plane instance."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_http(url: str, *, timeout: float = 20.0) -> None:
    """Poll an HTTP endpoint until it responds or the timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=1)
            if response.status_code < 500:
                return
        except requests.RequestException:
            time.sleep(0.1)
    raise TimeoutError(f"service did not become ready at {url}")


def sha256_hex(body: bytes) -> str:
    """Return lowercase SHA-256 hex for deterministic digest comparisons."""
    return hashlib.sha256(body).hexdigest()


def write_json(path: Path, value: Any) -> None:
    """Write compact JSON to a workspace path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def copy_tree(source: Path, destination: Path) -> None:
    """Copy a fixture directory into an isolated workspace."""
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def seed_workspace(base: Path) -> dict[str, Path]:
    """Create an isolated runtime workspace with config, state, and reports."""
    for name in ("state", "reports", "config", "corpus"):
        target = base / name
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

    shutil.copytree(PII_HOME / "config", base / "config", dirs_exist_ok=True)
    system = json.loads((PII_HOME / "config" / "system.json").read_text(encoding="utf-8"))
    system["state_dir"] = str(base / "state")
    system["report_dir"] = str(base / "reports")
    system["corpus_dir"] = str(base / "corpus")
    system["policy_file"] = str(base / "config" / "policy.json")
    system["source_file"] = str(base / "config" / "sources.json")
    system["listen"] = f"127.0.0.1:{free_port()}"
    write_json(base / "config" / "system.json", system)

    return {
        "root": base,
        "config": base / "config" / "system.json",
        "state": base / "state",
        "reports": base / "reports",
        "corpus": base / "corpus",
        "endpoint": f"http://{system['listen']}",
    }


def configure_single_source(workspace: dict[str, Path], source_id: str, corpus_dir: Path) -> None:
    """Point one configured source root at a fixture corpus directory."""
    sources = {
        "generation": "verifier-fixture-v1",
        "sources": [
            {
                "id": source_id,
                "root": str(corpus_dir),
                "department": "engineering",
                "region": "na",
                "required": True,
            }
        ],
    }
    write_json(workspace["root"] / "config" / "sources.json", sources)


def configure_multi_source(workspace: dict[str, Path], entries: list[dict[str, Any]]) -> None:
    """Replace the configured source registry for multi-source scenarios."""
    write_json(
        workspace["root"] / "config" / "sources.json",
        {"generation": "verifier-fixture-v1", "sources": entries},
    )


def run_cmd(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: float = 120,
) -> subprocess.CompletedProcess[str]:
    """Run a public task command and capture stdout/stderr."""
    merged = os.environ.copy()
    merged["PII_HOME"] = str(PII_HOME)
    if env:
        merged.update(env)
    return subprocess.run(
        args,
        cwd=str(cwd),
        env=merged,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def piictl(workspace: dict[str, Path], *args: str, headers: dict[str, str] | None = None) -> requests.Response:
    """Call the HTTP API the same way piictl would for a workspace endpoint."""
    command = list(args)
    method = "GET"
    path = "/health"
    body: dict[str, Any] | None = None
    if not command:
        raise ValueError("piictl command required")
    if command[0] == "health":
        path = "/health"
    elif command[0] == "metrics":
        path = "/v1/status"
    elif command[0] == "source" and len(command) > 1 and command[1] == "list":
        path = "/v1/sources"
    elif command[0] == "policy" and len(command) > 1 and command[1] == "list":
        path = "/v1/policies"
    elif command[0] == "job":
        if "create" in command:
            method = "POST"
            path = "/v1/jobs"
            idx = command.index("--id") + 1
            body = {
                "id": command[idx],
                "policy_version": command[command.index("--policy") + 1],
                "corpus_digest": command[command.index("--corpus-digest") + 1],
            }
        elif "cancel" in command:
            method = "POST"
            path = f"/v1/jobs/{command[command.index('--id') + 1]}/cancel"
        elif "status" in command:
            path = f"/v1/jobs/{command[command.index('--id') + 1]}"
    elif command[0] == "report":
        job = command[command.index("--job") + 1]
        if "export" in command:
            fmt = command[command.index("--format") + 1] if "--format" in command else "json"
            path = f"/v1/reports/{job}/export?format={fmt}"
        else:
            path = f"/v1/reports/{job}"
    else:
        raise ValueError(f"unsupported piictl command: {' '.join(command)}")

    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    return requests.request(
        method,
        workspace["endpoint"] + path,
        json=body,
        headers=request_headers,
        timeout=30,
    )


def worker_scan_once(
    workspace: dict[str, Path],
    *,
    source_root: Path,
    source_id: str,
    job_id: str,
    shard_id: str,
    generation: int,
    policy_digest: str,
    lease_token: str,
    session_id: str,
    attempt: int = 1,
    department: str = "engineering",
    region: str = "na",
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    """Run one offline worker scan and return the emitted result batch JSON."""
    args = [
        str(WORKER),
        "--scan-once",
        "--tenant",
        TENANT,
        "--job",
        job_id,
        "--shard",
        shard_id,
        "--generation",
        str(generation),
        "--policy-digest",
        policy_digest,
        "--corpus-digest",
        "verifier-corpus",
        "--worker-id",
        "verifier-worker",
        "--session-id",
        session_id,
        "--attempt",
        str(attempt),
        "--lease-token",
        lease_token,
        "--source-root",
        str(source_root),
        "--source-id",
        source_id,
        "--department",
        department,
        "--region",
        region,
        "--fingerprint-key",
        FINGERPRINT_KEY,
        "--checkpoints",
        str(workspace["state"] / "worker-checkpoints"),
    ]
    if extra_args:
        args.extend(extra_args)
    result = run_cmd(args, cwd=workspace["root"])
    if result.returncode != 0:
        raise RuntimeError(f"pii-worker failed:\n{result.stdout}\n{result.stderr}")
    return json.loads(result.stdout)


def register_worker(endpoint: str, worker_id: str = "verifier-worker", session_id: str = "session-a") -> None:
    """Register a compatible worker session with the control plane."""
    payload = {
        "worker_id": worker_id,
        "session_id": session_id,
        "detector_bundle": "builtin-1",
        "formats": ["csv", "email", "json", "ndjson", "properties", "text", "xml", "zip"],
    }
    response = requests.post(f"{endpoint}/v1/workers/register", json=payload, timeout=10)
    assert response.status_code == 201, response.text
    heartbeat = requests.post(
        f"{endpoint}/v1/workers/heartbeat",
        json={"worker_id": worker_id, "session_id": session_id},
        timeout=10,
    )
    assert heartbeat.status_code == 200, heartbeat.text


def issue_lease(endpoint: str, worker_id: str = "verifier-worker", session_id: str = "session-a") -> dict[str, Any]:
    """Lease the next eligible shard for a registered worker."""
    response = requests.post(
        f"{endpoint}/v1/workers/lease",
        json={"worker_id": worker_id, "session_id": session_id},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    return response.json()


def ingest_batch(endpoint: str, lease: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    """Submit one worker result batch through the public ingestion API."""
    response = requests.post(
        f"{endpoint}/v1/results",
        json={"lease": lease, "batch": batch},
        timeout=30,
    )
    return {"status": response.status_code, "body": response.json() if response.content else {}}


def create_job(
    endpoint: str,
    job_id: str,
    policy_version: str,
    corpus_digest: str = "verifier-corpus",
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create and start a scan job through the HTTP API."""
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    response = requests.post(
        f"{endpoint}/v1/jobs",
        json={"id": job_id, "policy_version": policy_version, "corpus_digest": corpus_digest},
        headers=request_headers,
        timeout=10,
    )
    assert response.status_code == 201, response.text
    return response.json()


def current_policy(endpoint: str) -> dict[str, Any]:
    """Return the active published policy from the control plane."""
    response = requests.get(f"{endpoint}/v1/policies", timeout=10)
    assert response.status_code == 200, response.text
    policies = response.json()
    assert policies, "policy registry is empty"
    return policies[0]


def scan_source_once(
    workspace: dict[str, Path],
    *,
    source_root: Path,
    source_id: str,
    job_id: str | None = None,
    department: str = "engineering",
    region: str = "na",
) -> dict[str, Any]:
    """Drive one end-to-end shard scan via worker, lease, and ingest APIs."""
    endpoint = workspace["endpoint"]
    register_worker(endpoint)
    policy = current_policy(endpoint)
    job_id = job_id or f"job-{source_id}"
    job = create_job(endpoint, job_id, policy["version"])
    lease = issue_lease(endpoint)
    batch = worker_scan_once(
        workspace,
        source_root=source_root,
        source_id=source_id,
        job_id=job["id"],
        shard_id=lease["shard_id"],
        generation=lease["generation"],
        policy_digest=lease["policy_digest"],
        lease_token=lease["token"],
        session_id=lease["session_id"],
        department=department,
        region=region,
    )
    receipt = ingest_batch(endpoint, lease, batch)
    return {"job": job, "lease": lease, "batch": batch, "receipt": receipt}


def report_for(
    workspace: dict[str, Path],
    job_id: str,
    principal: str | None = None,
) -> dict[str, Any]:
    """Fetch a report view, optionally scoped to a fixture principal."""
    headers = principal_header(principal) if principal else None
    response = piictl(workspace, "report", "show", "--job", job_id, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def export_for(
    workspace: dict[str, Path],
    job_id: str,
    fmt: str,
    principal: str | None = None,
) -> bytes:
    """Export a report view in JSON or CSV form."""
    headers = principal_header(principal) if principal else None
    response = piictl(workspace, "report", "export", "--job", job_id, "--format", fmt, headers=headers)
    assert response.status_code == 200, response.text
    return response.content


def contains_raw_pii(text: str) -> list[str]:
    """Return matched raw PII substrings from an operational surface."""
    import re

    hits: list[str] = []
    for pattern in RAW_PII_PATTERNS:
        hits.extend(re.findall(pattern, text))
    return hits


@contextmanager
def managed_server(config_path: Path) -> Iterator[str]:
    """Start pii-control against an isolated config file and stop it on exit."""
    env = os.environ.copy()
    env["PII_CONFIG"] = str(config_path)
    env["PII_HOME"] = str(PII_HOME)
    process = subprocess.Popen(
        [str(CONTROL), "serve", "--config", str(config_path)],
        cwd=str(PII_HOME),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    listen = json.loads(config_path.read_text(encoding="utf-8"))["listen"]
    endpoint = f"http://{listen}"
    try:
        wait_http(f"{endpoint}/health")
        yield endpoint
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


@pytest.fixture(scope="session", autouse=True)
def built_artifacts() -> None:
    """Rebuild submitted artifacts once before the verifier suite runs."""
    if not BUILD.is_file():
        pytest.fail(f"missing build script at {BUILD}")
    result = run_cmd([str(BUILD)], cwd=PII_HOME, timeout=600)
    if result.returncode != 0:
        pytest.fail(f"build.sh failed:\n{result.stdout}\n{result.stderr}")
    for binary in (CONTROL, PIICTL, WORKER):
        if not binary.exists():
            pytest.fail(f"missing built command: {binary}")


@pytest.fixture
def workspace(tmp_path: Path) -> Iterator[dict[str, Path]]:
    """Provide an isolated control-plane workspace for one test."""
    paths = seed_workspace(tmp_path / "pii")
    with managed_server(paths["config"]) as endpoint:
        paths["endpoint"] = endpoint
        yield paths
