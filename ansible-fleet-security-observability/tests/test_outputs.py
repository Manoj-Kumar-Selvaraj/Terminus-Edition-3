"""Live-state and metamorphic checks for fleet harden posture."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest
import requests

VAR = Path("/app/var/fleet-harden")
EDGES = Path("/app/edges")
ANSIBLE = Path("/app/environment/ansible")
EVIDENCE = Path("/app/environment/evidence")
REPORT = VAR / "posture-report.json"
TARGETS = VAR / "scrape" / "targets.json"
STAMP_PATH = EVIDENCE / "patch-stamp.txt"
FINDINGS_PATH = EVIDENCE / "audit-findings.json"

REQUIRED_PACKAGES = ["ca-certificates", "curl", "procps", "python3"]

EDGE_SPEC = {
    "app": {
        "root": EDGES / "app",
        "role": "app",
        "host": "edge-app",
        "metrics_port": 9100,
        "audit_port": 7375,
        "promtail_port": 9080,
        "falco_port": 8765,
    },
    "data": {
        "root": EDGES / "data",
        "role": "data",
        "host": "edge-data",
        "metrics_port": 9110,
        "audit_port": 7385,
        "promtail_port": 9090,
        "falco_port": 8775,
    },
    "ops": {
        "root": EDGES / "ops",
        "role": "ops",
        "host": "edge-ops",
        "metrics_port": 9120,
        "audit_port": 7395,
        "promtail_port": 9105,
        "falco_port": 8785,
    },
}

CHECK_KEYS = (
    "inventory",
    "packages",
    "packages_seal",
    "patch",
    "auditd",
    "metrics",
    "promtail",
    "falco",
    "firewall",
    "ssh",
    "scrape",
    "chain",
    "idempotent",
)

_PROCS: list[subprocess.Popen] = []


def _stamp() -> str:
    return STAMP_PATH.read_text(encoding="utf-8").strip()


def _findings() -> dict:
    return json.loads(FINDINGS_PATH.read_text(encoding="utf-8"))


def _expected_token(spec: dict) -> str:
    raw = (
        f"{spec['host']}|{spec['role']}|{spec['audit_port']}|"
        f"{spec['metrics_port']}|{spec['promtail_port']}|{spec['falco_port']}"
    ).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _kill_port(port: int) -> None:
    subprocess.run(
        ["bash", "-lc", f"fuser -k {port}/tcp >/dev/null 2>&1 || true"],
        check=False,
    )


def _start_listener(script: Path, port: int) -> None:
    _kill_port(port)
    log = script.with_suffix(".verifier.log")
    err = script.with_suffix(".verifier.err")
    proc = subprocess.Popen(
        ["python3", str(script)],
        stdout=log.open("w", encoding="utf-8"),
        stderr=err.open("w", encoding="utf-8"),
        start_new_session=True,
    )
    _PROCS.append(proc)
    deadline = time.time() + 20
    while time.time() < deadline:
        if proc.poll() is not None:
            raise AssertionError(f"listener exited early: {script} code={proc.returncode}")
        import socket

        with socket.socket() as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise AssertionError(f"listener did not bind {port}: {script}")


def _stop_all() -> None:
    for proc in _PROCS:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.terminate()
            except OSError:
                pass
    _PROCS.clear()
    for spec in EDGE_SPEC.values():
        for port in (
            spec["metrics_port"],
            spec["audit_port"],
            spec["promtail_port"],
            spec["falco_port"],
        ):
            _kill_port(int(port))


@pytest.fixture(scope="session", autouse=True)
def live_edges():
    """Reconstitute edge listeners from the agent-installed trees."""
    assert REPORT.is_file(), "missing posture-report.json"
    assert TARGETS.is_file(), "missing scrape/targets.json"
    assert ANSIBLE.is_dir(), "missing ansible tree artifact"

    # Start audit first, then metrics, then promtail (pulls audit), then falco (pulls promtail).
    for name, spec in EDGE_SPEC.items():
        root = Path(spec["root"])
        assert (root / "var/lib/fleet-harden/stage-09.ok").is_file(), f"{name} missing stage-09"
        _start_listener(root / "lib/fleet-auditd.py", int(spec["audit_port"]))
    for name, spec in EDGE_SPEC.items():
        root = Path(spec["root"])
        _start_listener(root / "lib/fleet-node-exporter.py", int(spec["metrics_port"]))
    for name, spec in EDGE_SPEC.items():
        root = Path(spec["root"])
        _start_listener(root / "lib/fleet-promtail.py", int(spec["promtail_port"]))
    for name, spec in EDGE_SPEC.items():
        root = Path(spec["root"])
        _start_listener(root / "lib/fleet-falco.py", int(spec["falco_port"]))
    try:
        yield
    finally:
        _stop_all()


def test_posture_report_schema_and_stamp():
    """Posture report must match the contract schema and authoritative stamp."""
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    findings = _findings()
    assert report["status"] == "ok"
    assert report["patch_stamp"] == _stamp()
    assert report["scrape_cidr"] == "172.28.0.0/16"
    assert report["edges"] == ["edge-app", "edge-data", "edge-ops"]
    assert report["required_controls"] == findings["required_controls"]
    assert set(report["checks"]) == set(CHECK_KEYS)
    assert all(report["checks"][k] is True for k in CHECK_KEYS)
    targets = json.loads(TARGETS.read_text(encoding="utf-8"))
    assert report["scrape_targets"] == targets


def test_edge_stage_markers_inventory_and_package_seal():
    """Each edge must have ordered stages, faithful inventory, stamp, and package seal."""
    for name, spec in EDGE_SPEC.items():
        root = Path(spec["root"])
        for stage in range(1, 10):
            marker = root / "var/lib/fleet-harden" / f"stage-{stage:02d}.ok"
            assert marker.is_file(), f"{name} missing {marker.name}"
        inv = json.loads((root / "var/lib/fleet-harden/inventory.json").read_text(encoding="utf-8"))
        assert inv["role"] == spec["role"]
        assert inv["hostname"] == spec["host"]
        assert inv["metrics_port"] == spec["metrics_port"]
        assert inv["audit_port"] == spec["audit_port"]
        assert inv["promtail_port"] == spec["promtail_port"]
        assert inv["falco_port"] == spec["falco_port"]
        assert inv["chain_token"] == _expected_token(spec)
        stamp = (root / "etc/fleet-harden/patch-stamp").read_text(encoding="utf-8").strip()
        assert stamp == _stamp()
        assert not stamp.startswith("DECOY-")
        seal = json.loads((root / "var/lib/fleet-harden/packages.seal").read_text(encoding="utf-8"))
        assert sorted(seal) == REQUIRED_PACKAGES


def test_firewall_and_ssh_interact_with_metrics_port():
    """Firewall allow/deny and SSH hardening must match the contract lines."""
    for name, spec in EDGE_SPEC.items():
        root = Path(spec["root"])
        port = spec["metrics_port"]
        fw = (root / "etc/fleet-harden/nft.allow").read_text(encoding="utf-8")
        assert f"allow tcp {port} from 172.28.0.0/16" in fw
        assert f"deny tcp {port} from 0.0.0.0/0" in fw
        assert f"allow tcp {port} from 0.0.0.0/0" not in fw
        ssh = (root / "etc/fleet-harden/sshd_snippet").read_text(encoding="utf-8")
        assert "PasswordAuthentication no" in ssh
        assert "PasswordAuthentication yes" not in ssh
        assert "PermitRootLogin no" in ssh
        assert "MaxAuthTries 3" in ssh


def test_promtail_and_falco_wire_cross_ports():
    """Promtail must cite audit; falco rules must cite metrics/audit/promtail."""
    for name, spec in EDGE_SPEC.items():
        root = Path(spec["root"])
        promtail = (root / "etc/fleet-harden/promtail.yml").read_text(encoding="utf-8")
        assert "http://loki.fleet.internal:3100" in promtail
        assert f"audit_bridge: 127.0.0.1:{spec['audit_port']}" in promtail
        assert f"metrics_port: {spec['metrics_port']}" in promtail
        falco = (root / "etc/fleet-harden/falco-rules.yml").read_text(encoding="utf-8")
        assert f"metrics_port: {spec['metrics_port']}" in falco
        assert f"audit_port: {spec['audit_port']}" in falco
        assert f"promtail_port: {spec['promtail_port']}" in falco


def test_live_listeners_and_observability_chain():
    """Reconstituted listeners must serve role labels and the live audit→promtail→falco chain."""
    for name, spec in EDGE_SPEC.items():
        token = _expected_token(spec)

        metrics = requests.get(f"http://127.0.0.1:{spec['metrics_port']}/metrics", timeout=5)
        assert metrics.status_code == 200
        assert f'fleet_node_up{{fleet_role="{spec["role"]}"}} 1' in metrics.text

        audit = requests.get(f"http://127.0.0.1:{spec['audit_port']}/healthz", timeout=5)
        assert audit.status_code == 200
        audit_doc = audit.json()
        assert audit_doc["component"] == "auditd"
        assert audit_doc["chain_token"] == token

        ready = requests.get(f"http://127.0.0.1:{spec['promtail_port']}/ready", timeout=5)
        assert ready.status_code == 200
        ready_doc = ready.json()
        assert str(spec["audit_port"]) in ready.text
        assert ready_doc.get("audit_token") == token

        falco = requests.get(f"http://127.0.0.1:{spec['falco_port']}/healthz", timeout=5)
        assert falco.status_code == 200
        falco_doc = falco.json()
        assert str(spec["metrics_port"]) in falco.text
        assert str(spec["promtail_port"]) in falco.text
        assert token in falco_doc.get("wire", "")


def test_scrape_targets_order_and_chain_tokens():
    """Scrape targets must be app→data→ops with inventory-faithful roles and tokens."""
    targets = json.loads(TARGETS.read_text(encoding="utf-8"))
    assert [t["host"] for t in targets] == ["edge-app", "edge-data", "edge-ops"]
    by_host = {t["host"]: t for t in targets}
    for name, spec in EDGE_SPEC.items():
        inv = json.loads(
            (Path(spec["root"]) / "var/lib/fleet-harden/inventory.json").read_text(encoding="utf-8")
        )
        row = by_host[spec["host"]]
        assert row["port"] == inv["metrics_port"] == spec["metrics_port"]
        assert row["fleet_role"] == inv["role"] == spec["role"]
        assert row["chain_token"] == inv["chain_token"] == _expected_token(spec)


def test_control_stage_markers_present():
    """Control seal markers stage-10 and stage-11 must exist."""
    assert (VAR / "stage-10.ok").is_file()
    assert (VAR / "stage-11.ok").is_file()


def test_metamorphic_reapply_keeps_contract():
    """Re-running the artifacted playbook must preserve live contract state."""
    before = REPORT.read_text(encoding="utf-8")
    before_targets = TARGETS.read_text(encoding="utf-8")
    env = os.environ.copy()
    env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
    env["ANSIBLE_RETRY_FILES_ENABLED"] = "False"
    env["ANSIBLE_LOCALHOST_WARNING"] = "False"
    completed = subprocess.run(
        ["/app/bin/fleet-harden-apply"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    after = json.loads(REPORT.read_text(encoding="utf-8"))
    assert after["status"] == "ok"
    assert after["patch_stamp"] == _stamp()
    assert after["scrape_cidr"] == "172.28.0.0/16"
    assert after["edges"] == ["edge-app", "edge-data", "edge-ops"]
    assert json.loads(TARGETS.read_text(encoding="utf-8")) == json.loads(before_targets)
    time.sleep(1)
    for name, spec in EDGE_SPEC.items():
        metrics = requests.get(f"http://127.0.0.1:{spec['metrics_port']}/metrics", timeout=5)
        assert metrics.status_code == 200
        assert f'fleet_node_up{{fleet_role="{spec["role"]}"}} 1' in metrics.text
        falco = requests.get(f"http://127.0.0.1:{spec['falco_port']}/healthz", timeout=5)
        assert falco.status_code == 200
        assert _expected_token(spec) in falco.json().get("wire", "")
    assert json.loads(before)["scrape_targets"] == after["scrape_targets"]
