"""Verifier for the HTTP Terraform backend concurrency incident.

Starts the submitted backend as a separate process, drives HTTP protocol
cases with deterministic barriers (no wall-clock races), runs real Terraform
CLI clients, and grades live remote state plus audit export.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import threading
import time
import uuid
from http.client import HTTPConnection
from pathlib import Path

import pytest

BACKEND_SRC = Path("/app/backend")
BIN_DIR = Path("/app/bin")
TERRAFORM_DIR = Path("/app/terraform")
DATA_DIR = Path("/app/var/backend-store")
OUTPUT_DIR = Path("/app/output")
PORT = int(os.environ.get("BACKEND_PORT", "18765"))
BASE = f"http://127.0.0.1:{PORT}"
ENV = {
    **os.environ,
    "TF_CLI_CONFIG_FILE": "/app/terraform.tfrc",
    "TF_IN_AUTOMATION": "1",
    "CHECKPOINT_DISABLE": "1",
    "BACKEND_HOST": "127.0.0.1",
    "BACKEND_PORT": str(PORT),
    "BACKEND_DATA_DIR": str(DATA_DIR),
    "LEASE_TTL_TICKS": "10",
}


def _http(
    method: str,
    path: str,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes]:
    conn = HTTPConnection("127.0.0.1", PORT, timeout=10)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def _json(
    method: str,
    path: str,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    raw = None if payload is None else json.dumps(payload).encode("utf-8")
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    status, data = _http(method, path, raw, hdrs)
    if not data:
        return status, {}
    try:
        return status, json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        return status, {"_raw": data.decode("utf-8", errors="replace")}


def _wait_health(timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, payload = _json("GET", "/v1/control/health")
            if status == 200 and payload.get("ok") is True:
                return
        except OSError:
            pass
        time.sleep(0.05)
    raise AssertionError("backend failed to become healthy")


def _reset_data() -> None:
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def backend():
    """Launch submitted backend against a fresh durable store."""
    assert BACKEND_SRC.is_dir(), "missing /app/backend artifact"
    assert (BIN_DIR / "http-backend").exists(), "missing /app/bin/http-backend"
    _reset_data()
    log_path = DATA_DIR / "verifier-backend.log"
    proc = subprocess.Popen(
        ["python3", str(BIN_DIR / "http-backend")],
        env=ENV,
        stdout=log_path.open("w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        _wait_health()
        yield proc
    finally:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)


def _state_doc(serial: int, lineage: str, marker: str) -> dict:
    return {
        "version": 4,
        "terraform_version": "1.9.8",
        "serial": serial,
        "lineage": lineage,
        "outputs": {"marker": {"value": marker, "type": "string"}},
        "resources": [],
    }


def _lock_info(lock_id: str, who: str) -> dict:
    return {
        "ID": lock_id,
        "Operation": "OperationTypeApply",
        "Info": "",
        "Who": who,
        "Version": "1.9.8",
        "Created": "2026-01-01T00:00:00Z",
        "Path": "",
    }


def test_artifacts_present():
    """Required backend, operator, terraform, and config artifacts must exist."""
    assert BACKEND_SRC.is_dir()
    assert (BIN_DIR / "http-backend").exists()
    assert (BIN_DIR / "operator-apply").exists()
    assert (BIN_DIR / "export-audit").exists()
    assert (TERRAFORM_DIR / "workspaces/prod").is_dir()
    assert (TERRAFORM_DIR / "workspaces/stage").is_dir()
    assert Path("/app/terraform.tfrc").exists()


def test_lock_owner_token_fences_state_write(backend):
    """State commits require the active workspace lock token."""
    lid = str(uuid.uuid4())
    status, _ = _json("LOCK", "/v1/workspaces/prod/lock", _lock_info(lid, "owner-a"))
    assert status == 200
    body = json.dumps(_state_doc(1, "lin-a", "x")).encode("utf-8")
    bad_status, _ = _http(
        "POST",
        "/v1/workspaces/prod/state",
        body,
        {"Content-Type": "application/json", "Lock-ID": "wrong-token"},
    )
    assert bad_status >= 400
    get_status, _ = _http("GET", "/v1/workspaces/prod/state")
    assert get_status == 404
    ok_status, _ = _http(
        "POST",
        "/v1/workspaces/prod/state",
        body,
        {"Content-Type": "application/json", "Lock-ID": lid},
    )
    assert ok_status == 200
    get_status, remote = _http("GET", "/v1/workspaces/prod/state")
    assert get_status == 200
    assert json.loads(remote.decode("utf-8"))["serial"] == 1


def test_second_lock_blocked_until_release(backend):
    """Two applies on one workspace cannot both hold an unexpired lease."""
    a = str(uuid.uuid4())
    b = str(uuid.uuid4())
    barrier = threading.Event()
    results: dict[str, int] = {}

    def client_a() -> None:
        status, _ = _json("LOCK", "/v1/workspaces/prod/lock", _lock_info(a, "run-a"))
        results["a_lock"] = status
        barrier.set()
        # Hold until client B has attempted.
        time.sleep(0.2)
        _json("UNLOCK", "/v1/workspaces/prod/lock", _lock_info(a, "run-a"))

    def client_b() -> None:
        barrier.wait(timeout=5)
        status, _ = _json("LOCK", "/v1/workspaces/prod/lock", _lock_info(b, "run-b"))
        results["b_lock"] = status

    t1 = threading.Thread(target=client_a)
    t2 = threading.Thread(target=client_b)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)
    assert results.get("a_lock") == 200
    assert results.get("b_lock") == 423


def test_workspace_isolation_allows_parallel_locks(backend):
    """A prod lease must not block an independent stage lease."""
    prod = str(uuid.uuid4())
    stage = str(uuid.uuid4())
    s1, _ = _json("LOCK", "/v1/workspaces/prod/lock", _lock_info(prod, "prod-run"))
    s2, _ = _json("LOCK", "/v1/workspaces/stage/lock", _lock_info(stage, "stage-run"))
    assert s1 == 200 and s2 == 200
    body_prod = json.dumps(_state_doc(1, "lin-prod", "p")).encode("utf-8")
    body_stage = json.dumps(_state_doc(1, "lin-stage", "s")).encode("utf-8")
    assert (
        _http(
            "POST",
            "/v1/workspaces/prod/state",
            body_prod,
            {"Content-Type": "application/json", "Lock-ID": prod},
        )[0]
        == 200
    )
    assert (
        _http(
            "POST",
            "/v1/workspaces/stage/state",
            body_stage,
            {"Content-Type": "application/json", "Lock-ID": stage},
        )[0]
        == 200
    )
    _, prod_state = _http("GET", "/v1/workspaces/prod/state")
    _, stage_state = _http("GET", "/v1/workspaces/stage/state")
    assert json.loads(prod_state)["lineage"] == "lin-prod"
    assert json.loads(stage_state)["lineage"] == "lin-stage"
    assert json.loads(prod_state)["outputs"]["marker"]["value"] == "p"
    assert json.loads(stage_state)["outputs"]["marker"]["value"] == "s"


def test_stale_serial_and_lineage_rejected(backend):
    """Stale serial or foreign lineage must not overwrite newer remote state."""
    lid = str(uuid.uuid4())
    assert _json("LOCK", "/v1/workspaces/prod/lock", _lock_info(lid, "owner"))[0] == 200
    first = json.dumps(_state_doc(1, "lin-1", "v1")).encode("utf-8")
    assert (
        _http(
            "POST",
            "/v1/workspaces/prod/state",
            first,
            {"Content-Type": "application/json", "Lock-ID": lid},
        )[0]
        == 200
    )
    stale_serial = json.dumps(_state_doc(1, "lin-1", "stale")).encode("utf-8")
    status, _ = _http(
        "POST",
        "/v1/workspaces/prod/state",
        stale_serial,
        {"Content-Type": "application/json", "Lock-ID": lid},
    )
    assert status >= 400
    bad_lineage = json.dumps(_state_doc(2, "lin-OTHER", "x")).encode("utf-8")
    status, _ = _http(
        "POST",
        "/v1/workspaces/prod/state",
        bad_lineage,
        {"Content-Type": "application/json", "Lock-ID": lid},
    )
    assert status >= 400
    _, remote = _http("GET", "/v1/workspaces/prod/state")
    doc = json.loads(remote)
    assert doc["serial"] == 1
    assert doc["outputs"]["marker"]["value"] == "v1"


def test_lost_response_idempotent_commit(backend):
    """Retrying a committed POST with the same idempotency key must not bump serial twice."""
    lid = str(uuid.uuid4())
    assert _json("LOCK", "/v1/workspaces/prod/lock", _lock_info(lid, "owner"))[0] == 200
    body = json.dumps(_state_doc(1, "lin-idem", "once")).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Lock-ID": lid,
        "Idempotency-Key": "apply-1",
    }
    assert _http("POST", "/v1/workspaces/prod/state", body, headers)[0] == 200
    # Simulate lost response: identical retry.
    assert _http("POST", "/v1/workspaces/prod/state", body, headers)[0] == 200
    _, remote = _http("GET", "/v1/workspaces/prod/state")
    assert json.loads(remote)["serial"] == 1
    # Export audit and ensure a single logical commit serial.
    proc = subprocess.run(
        ["python3", str(BIN_DIR / "export-audit")],
        env=ENV,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    audit = json.loads((OUTPUT_DIR / "audit.json").read_text(encoding="utf-8"))
    commits = [
        e
        for e in audit["events"]
        if e["event"] == "state_committed" and e["workspace"] == "prod"
    ]
    assert len(commits) == 1
    assert commits[0]["detail"]["serial"] == 1


def test_lease_expiry_via_control_clock(backend):
    """Only an expired lease may be reclaimed after deterministic clock advance."""
    lid = str(uuid.uuid4())
    assert _json("LOCK", "/v1/workspaces/prod/lock", _lock_info(lid, "old"))[0] == 200
    other = str(uuid.uuid4())
    blocked, _ = _json("LOCK", "/v1/workspaces/prod/lock", _lock_info(other, "new"))
    assert blocked == 423
    adv, payload = _json("POST", "/v1/control/advance", {"ticks": 11})
    assert adv == 200 and payload["tick"] >= 11
    ok, _ = _json("LOCK", "/v1/workspaces/prod/lock", _lock_info(other, "new"))
    assert ok == 200


def test_restart_after_lock_and_commit(backend):
    """Backend restart must preserve committed state and continue fencing."""
    lid = str(uuid.uuid4())
    assert _json("LOCK", "/v1/workspaces/prod/lock", _lock_info(lid, "owner"))[0] == 200
    body = json.dumps(_state_doc(1, "lin-restart", "persist")).encode("utf-8")
    assert (
        _http(
            "POST",
            "/v1/workspaces/prod/state",
            body,
            {"Content-Type": "application/json", "Lock-ID": lid},
        )[0]
        == 200
    )
    assert _json("UNLOCK", "/v1/workspaces/prod/lock", _lock_info(lid, "owner"))[0] == 200

    # Kill and relaunch against the same durable DB.
    try:
        os.killpg(backend.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    backend.wait(timeout=5)

    log_path = DATA_DIR / "verifier-backend-restart.log"
    restarted = subprocess.Popen(
        ["python3", str(BIN_DIR / "http-backend")],
        env=ENV,
        stdout=log_path.open("w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        _wait_health()
        status, remote = _http("GET", "/v1/workspaces/prod/state")
        assert status == 200
        doc = json.loads(remote)
        assert doc["serial"] == 1
        assert doc["lineage"] == "lin-restart"
        # Stale overwrite still rejected after restart.
        lid2 = str(uuid.uuid4())
        assert _json("LOCK", "/v1/workspaces/prod/lock", _lock_info(lid2, "owner2"))[0] == 200
        stale = json.dumps(_state_doc(1, "lin-restart", "nope")).encode("utf-8")
        bad, _ = _http(
            "POST",
            "/v1/workspaces/prod/state",
            stale,
            {"Content-Type": "application/json", "Lock-ID": lid2},
        )
        assert bad >= 400
    finally:
        try:
            os.killpg(restarted.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        restarted.wait(timeout=5)


def _tf_env() -> dict[str, str]:
    return dict(ENV)


def _clean_tf_workspace(name: str) -> Path:
    root = TERRAFORM_DIR / "workspaces" / name
    for rel in (".terraform", "terraform.tfstate", "terraform.tfstate.backup"):
        path = root / rel
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    # Keep lockfile if present; otherwise init will recreate from mirror.
    return root


def test_terraform_apply_prod_and_stage(backend):
    """Real Terraform CLI applies must commit isolated remote state for prod and stage."""
    prod = _clean_tf_workspace("prod")
    stage = _clean_tf_workspace("stage")
    env = _tf_env()
    env["TF_VAR_marker"] = "tf-prod"
    p1 = subprocess.run(
        ["python3", str(BIN_DIR / "operator-apply"), "--workspace", "prod", "--marker", "tf-prod"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert p1.returncode == 0, p1.stdout + p1.stderr
    env["TF_VAR_marker"] = "tf-stage"
    p2 = subprocess.run(
        ["python3", str(BIN_DIR / "operator-apply"), "--workspace", "stage", "--marker", "tf-stage"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert p2.returncode == 0, p2.stdout + p2.stderr
    _, prod_state = _http("GET", "/v1/workspaces/prod/state")
    _, stage_state = _http("GET", "/v1/workspaces/stage/state")
    prod_doc = json.loads(prod_state)
    stage_doc = json.loads(stage_state)
    assert prod_doc["serial"] >= 1
    assert stage_doc["serial"] >= 1
    assert prod_doc["lineage"] != stage_doc["lineage"]
    assert (prod / ".terraform.lock.hcl").exists()
    assert (stage / ".terraform.lock.hcl").exists()


def test_two_terraform_applies_same_workspace_serialize(backend):
    """Two concurrent Terraform applies on prod must not both mutate under split leases."""
    root = _clean_tf_workspace("prod")
    env = _tf_env()
    init = subprocess.run(
        ["terraform", "init", "-input=false", "-reconfigure"],
        cwd=str(root),
        env=env,
        text=True,
        capture_output=True,
    )
    assert init.returncode == 0, init.stdout + init.stderr
    seed = subprocess.run(
        ["terraform", "apply", "-input=false", "-auto-approve", "-var", "marker=seed"],
        cwd=str(root),
        env=env,
        text=True,
        capture_output=True,
    )
    assert seed.returncode == 0, seed.stdout + seed.stderr

    results: list[int] = []
    barrier = threading.Barrier(2)

    def apply_marker(marker: str) -> None:
        barrier.wait(timeout=30)
        proc = subprocess.run(
            [
                "terraform",
                "apply",
                "-input=false",
                "-auto-approve",
                "-var",
                f"marker={marker}",
            ],
            cwd=str(root),
            env=env,
            text=True,
            capture_output=True,
        )
        results.append(proc.returncode)

    t1 = threading.Thread(target=apply_marker, args=("concurrent-a",))
    t2 = threading.Thread(target=apply_marker, args=("concurrent-b",))
    t1.start()
    t2.start()
    t1.join(timeout=180)
    t2.join(timeout=180)
    assert any(code == 0 for code in results), results
    _, remote = _http("GET", "/v1/workspaces/prod/state")
    doc = json.loads(remote)
    assert doc["serial"] >= 2
    marker = doc.get("outputs", {}).get("marker", {}).get("value")
    assert marker in {"concurrent-a", "concurrent-b"}


def test_unapproved_provider_rejected(backend):
    """Operator apply must fail closed when an unapproved provider package is present."""
    _clean_tf_workspace("prod")
    unapproved = Path("/tmp/unapproved-provider")
    if unapproved.exists():
        shutil.rmtree(unapproved)
    unapproved.mkdir(parents=True)
    (unapproved / "evil.zip").write_bytes(b"not-a-real-provider")
    env = _tf_env()
    env["UNAPPROVED_PROVIDER_DIR"] = str(unapproved)
    proc = subprocess.run(
        ["python3", str(BIN_DIR / "operator-apply"), "--workspace", "prod", "--marker", "x"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert proc.returncode != 0
    assert "unapproved" in (proc.stdout + proc.stderr).lower()


def test_audit_export_schema_and_workspace_fields(backend):
    """Audit export must follow the contract schema with per-workspace events."""
    lid = str(uuid.uuid4())
    assert _json("LOCK", "/v1/workspaces/stage/lock", _lock_info(lid, "stage"))[0] == 200
    body = json.dumps(_state_doc(1, "lin-audit", "a")).encode("utf-8")
    assert (
        _http(
            "POST",
            "/v1/workspaces/stage/state",
            body,
            {"Content-Type": "application/json", "Lock-ID": lid},
        )[0]
        == 200
    )
    proc = subprocess.run(
        ["python3", str(BIN_DIR / "export-audit")],
        env=ENV,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    audit = json.loads((OUTPUT_DIR / "audit.json").read_text(encoding="utf-8"))
    assert audit["schema_version"] == 1
    assert isinstance(audit["events"], list) and audit["events"]
    seqs = [e["seq"] for e in audit["events"]]
    assert seqs == sorted(seqs)
    assert any(e["workspace"] == "stage" and e["event"] == "state_committed" for e in audit["events"])


def test_counterexample_static_audit_alone_insufficient(backend):
    """A forged audit file without matching remote state must not satisfy live checks."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "audit.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "events": [
                    {
                        "seq": 1,
                        "tick": 0,
                        "workspace": "prod",
                        "event": "state_committed",
                        "detail": {"serial": 99, "lineage": "forged"},
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status, _ = _http("GET", "/v1/workspaces/prod/state")
    assert status == 404
