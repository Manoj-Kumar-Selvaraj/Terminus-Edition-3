"""Behavioral verifier for the sovereign layer-4 load balancer."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pytest

ROOT = Path(os.environ.get("SOVEREIGN_LB_HOME", "/app/sovereign-lb"))
BUILD = ROOT / "bin" / "build"
CONTROL = ROOT / "build" / "bin" / "lb-control-plane"
DATAPLANE = ROOT / "build" / "bin" / "lb-dataplane"
LBCTL = ROOT / "build" / "bin" / "lbctl"
LAB = ROOT / "bin" / "lab"
SCENARIO = ROOT / "config" / "scenarios" / "single-node-lab.json"
NODE_CONFIG = ROOT / "config" / "nodes" / "dp-01.json"
NODE_CONFIG_B = ROOT / "config" / "nodes" / "dp-02.json"


def scenario_desired() -> dict[str, Any]:
    return json.loads(SCENARIO.read_text(encoding="utf-8"))["desired"]


def write_desired(base: Path, desired: dict[str, Any], name: str = "desired.json") -> Path:
    path = base / name
    path.write_text(json.dumps(desired), encoding="utf-8")
    return path


def desired_path(base: Path) -> Path:
    return write_desired(base, scenario_desired())


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_port(host: str, port: int, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            try:
                sock.connect((host, port))
                return
            except OSError:
                time.sleep(0.1)
    raise TimeoutError(f"port {host}:{port} did not open")


def http_json(url: str, *, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any] | str]:
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Content-Type", "application/json")
    if headers:
        for key, value in headers.items():
            request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read()
            text = payload.decode() or "{}"
            try:
                return response.status, json.loads(text)
            except json.JSONDecodeError:
                return response.status, text
    except urllib.error.HTTPError as error:
        payload = error.read()
        try:
            return error.code, json.loads(payload.decode() or "{}")
        except json.JSONDecodeError:
            return error.code, {"error": payload.decode(errors="replace")}


def http_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read().decode()


@contextmanager
def managed_process(args: list[str], *, cwd: Path, env: dict[str, str]) -> Iterator[subprocess.Popen[str]]:
    process = subprocess.Popen(args, cwd=str(cwd), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    try:
        yield process
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


@pytest.fixture(scope="session", autouse=True)
def build_tree() -> None:
    if CONTROL.is_file() and DATAPLANE.is_file():
        return
    if not BUILD.is_file():
        raise RuntimeError(f"missing build script and binaries under {ROOT / 'build' / 'bin'}")
    subprocess.run([str(BUILD)], cwd=str(ROOT), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if not CONTROL.is_file() or not DATAPLANE.is_file():
        raise RuntimeError("build did not produce lb-control-plane and lb-dataplane binaries")


@pytest.fixture
def lab_state(tmp_path: Path) -> Path:
    return tmp_path / "lab"


@pytest.fixture
def control_state(tmp_path: Path) -> Path:
    path = tmp_path / "control"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def dataplane_state(tmp_path: Path) -> Path:
    path = tmp_path / "dp-01"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_node_config(base: Path, template: Path, control_port: int, status_port: int) -> Path:
    profile = json.loads(template.read_text(encoding="utf-8"))
    profile["control_port"] = control_port
    profile["status_address"] = f"127.0.0.1:{status_port}"
    profile["state_root"] = str(base)
    path = base / "node.json"
    path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    return path


@contextmanager
def running_stack(
    lab_state: Path,
    control_state: Path,
    dataplane_state: Path,
    *,
    extra_nodes: list[tuple[Path, Path]] | None = None,
) -> Iterator[dict[str, Any]]:
    management_port = free_port()
    control_port = free_port()
    status_port = free_port()
    node_config = write_node_config(dataplane_state, NODE_CONFIG, control_port, status_port)
    env = os.environ.copy()
    env["SOVEREIGN_LB_HOME"] = str(ROOT)
    extra_nodes = extra_nodes or []
    with managed_process([str(LAB), "start", "--state", str(lab_state)], cwd=ROOT, env=env):
        wait_port("127.0.0.1", 19001, timeout=15)
        with managed_process(
            [str(CONTROL), "-management", f"127.0.0.1:{management_port}", "-control", f"127.0.0.1:{control_port}", "-state", str(control_state)],
            cwd=ROOT,
            env=env,
        ):
            wait_port("127.0.0.1", management_port, timeout=15)
            node_processes: list[subprocess.Popen[str]] = []
            with managed_process([str(DATAPLANE), "--config", str(node_config)], cwd=ROOT, env=env) as primary:
                wait_port("127.0.0.1", status_port, timeout=15)
                for node_base, template in extra_nodes:
                    extra_status = free_port()
                    extra_config = write_node_config(node_base, template, control_port, extra_status)
                    proc = subprocess.Popen([str(DATAPLANE), "--config", str(extra_config)], cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    node_processes.append(proc)
                    wait_port("127.0.0.1", extra_status, timeout=15)
                time.sleep(0.5)
                try:
                    yield {
                        "management": f"http://127.0.0.1:{management_port}",
                        "control_port": control_port,
                        "status_port": status_port,
                    }
                finally:
                    for proc in node_processes:
                        if proc.poll() is None:
                            proc.terminate()
                            proc.wait(timeout=3)


def apply(endpoint: str, desired_file: Path, key: str) -> tuple[int, dict[str, Any]]:
    body = desired_file.read_bytes()
    status, payload = http_json(f"{endpoint}/v1/apply", method="POST", body=body, headers={"Idempotency-Key": key})
    assert isinstance(payload, dict)
    return status, payload


def wait_active(endpoint: str, timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, payload = http_json(f"{endpoint}/v1/status")
        assert status == 200 and isinstance(payload, dict)
        rollout = payload.get("rollout", {})
        if payload.get("active_generation") and rollout.get("phase") == "active":
            return
        time.sleep(0.25)
    raise TimeoutError("rollout did not reach active")


def recv_all(connection: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = connection.recv(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def expect_no_forwarding(host: str, port: int) -> None:
    try:
        with socket.create_connection((host, port), timeout=5) as client:
            client.settimeout(2.0)
            client.sendall(b"probe")
            assert recv_all(client, 1) == b""
    except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError, TimeoutError, OSError):
        return


def lab_events(lab_state: Path) -> list[dict[str, Any]]:
    events_path = lab_state / "events.json"
    if not events_path.is_file():
        return []
    return json.loads(events_path.read_text(encoding="utf-8"))


# --- P2P smoke ---


def test_p2p_binaries_and_catalog_present() -> None:
    assert CONTROL.is_file()
    assert DATAPLANE.is_file()
    assert LBCTL.is_file()
    assert SCENARIO.is_file()
    assert (ROOT / "config" / "fleet.json").is_file()


def test_p2p_validate_rejects_invalid_policy(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        desired = scenario_desired()
        desired["target_groups"][0]["policy"] = "magic-hash"
        path = write_desired(lab_state, desired, "invalid-policy.json")
        status, _payload = apply(stack["management"], path, "invalid-policy")
        assert status == 422


def test_p2p_idempotency_replay(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        first = apply(stack["management"], desired_path(lab_state), "idem-1")
        second = apply(stack["management"], desired_path(lab_state), "idem-1")
        assert first[0] in {200, 202}
        assert second[0] == 200
        assert first[1]["generation"] == second[1]["generation"]


def test_p2p_lbctl_status_command(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        proc = subprocess.run(
            [str(LBCTL), "-endpoint", stack["management"], "status"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        payload = json.loads(proc.stdout)
        assert "accepted_revision" in payload


# --- REQ_AUTHORITY ---


def test_f2p_same_revision_different_body_conflict(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "rev-1-a")[0] in {200, 202}
        mutated = scenario_desired()
        mutated["listeners"][0]["idle_timeout_ms"] = 31000
        status, payload = apply(stack["management"], write_desired(lab_state, mutated, "mutated.json"), "rev-1-b")
        assert status == 409
        assert "error" in payload


def test_f2p_accepted_digest_persisted(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "digest-store-1")[0] in {200, 202}
        authority = json.loads((control_state / "authority.json").read_text(encoding="utf-8"))
        assert authority.get("accepted_digest")
        assert len(str(authority["accepted_digest"])) == 64


def test_f2p_stale_revision_rejected(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "rev-2")[0] in {200, 202}
        stale = scenario_desired()
        stale["revision"] = 1
        status, _payload = apply(stack["management"], write_desired(lab_state, stale, "stale.json"), "rev-stale")
        assert status == 409


def test_f2p_idempotency_key_body_conflict(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "idem-body")[0] in {200, 202}
        mutated = scenario_desired()
        mutated["listeners"][0]["buffer_bytes"] = 65537
        status, _payload = apply(stack["management"], write_desired(lab_state, mutated, "idem-body-2.json"), "idem-body")
        assert status == 409


def test_f2p_revision_advances_accepted_authority(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "rev-a")[0] in {200, 202}
        desired = scenario_desired()
        desired["revision"] = 2
        assert apply(stack["management"], write_desired(lab_state, desired, "rev-b.json"), "rev-b")[0] in {200, 202}
        status, payload = http_json(f"{stack['management']}/v1/status")
        assert status == 200 and isinstance(payload, dict)
        assert payload["accepted_revision"] == 2


# --- REQ_CANONICAL ---


def test_f2p_generation_snapshot_matches_digest(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        _status, payload = apply(stack["management"], desired_path(lab_state), "canonical-1")
        generation = payload["generation"]
        gen_dir = control_state / "generations" / f"generation-{generation:020d}"
        canonical = (gen_dir / "snapshot.json").read_bytes().strip()
        digest = (gen_dir / "digest").read_text(encoding="utf-8").strip()
        assert hashlib.sha256(canonical).hexdigest() == digest


def test_f2p_duplicate_listener_bind_rejected(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        desired = scenario_desired()
        desired["listeners"].append(dict(desired["listeners"][0]))
        desired["listeners"][1]["name"] = "echo-dup"
        status, _payload = apply(stack["management"], write_desired(lab_state, desired, "dup-bind.json"), "dup-bind")
        assert status == 422


def test_f2p_invalid_listener_port_rejected(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        desired = scenario_desired()
        desired["listeners"][0]["port"] = 70000
        status, _payload = apply(stack["management"], write_desired(lab_state, desired, "bad-port.json"), "bad-port")
        assert status == 422


# --- REQ_ROLLOUT ---


def test_f2p_rollout_reaches_active_phase(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "rollout-1")[0] in {200, 202}
        wait_active(stack["management"])


def test_f2p_conflict_preserves_active_generation(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "preserve-1")[0] in {200, 202}
        wait_active(stack["management"])
        _, before = http_json(f"{stack['management']}/v1/status")
        conflict = scenario_desired()
        conflict["revision"] = 1
        conflict["listeners"][0]["idle_timeout_ms"] = 32000
        status, _payload = apply(stack["management"], write_desired(lab_state, conflict, "conflict.json"), "preserve-2")
        assert status == 409
        _, after = http_json(f"{stack['management']}/v1/status")
        assert isinstance(before, dict) and isinstance(after, dict)
        assert after.get("active_generation") == before.get("active_generation")


def test_f2p_quorum_requires_connected_nodes(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    desired = scenario_desired()
    desired["rollout"]["prepare_quorum"] = 1
    desired["rollout"]["activate_quorum"] = 2
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        status, _payload = apply(stack["management"], write_desired(lab_state, desired, "quorum.json"), "quorum-1")
        assert status in {200, 202}
        deadline = time.time() + 8
        while time.time() < deadline:
            _status, body = http_json(f"{stack['management']}/v1/status")
            assert isinstance(body, dict)
            if body.get("rollout", {}).get("phase") == "active":
                pytest.fail("rollout reached active without connected quorum")
            time.sleep(0.25)


def test_f2p_status_reports_rollout_present(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "status-rollout")[0] in {200, 202}
        status, payload = http_json(f"{stack['management']}/v1/status")
        assert status == 200 and isinstance(payload, dict)
        assert payload.get("rollout_present") is True


# --- REQ_STREAM ---


def test_f2p_multibuffer_tcp_echo(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "echo-1")[0] in {200, 202}
        wait_active(stack["management"])
        payload = b"terminus-echo-" + b"x" * 12000
        with socket.create_connection(("127.0.0.1", 18001), timeout=5) as client:
            client.sendall(payload)
            client.shutdown(socket.SHUT_WR)
            assert recv_all(client, len(payload)) == payload


def test_f2p_proxy_inspect_listener_echo(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "proxy-1")[0] in {200, 202}
        wait_active(stack["management"])
        time.sleep(1.0)
        with socket.create_connection(("127.0.0.1", 18005), timeout=5) as client:
            client.sendall(b"probe\n")
            assert recv_all(client, 6) == b"probe\n"


def test_f2p_half_close_backend_survives(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    desired = scenario_desired()
    desired["listeners"].append(
        {
            "name": "half",
            "address": "127.0.0.1",
            "port": 18003,
            "target_group": "half-pool",
            "proxy_protocol_v2": False,
            "connect_timeout_ms": 1000,
            "idle_timeout_ms": 30000,
            "buffer_bytes": 65536,
        }
    )
    desired["target_groups"].append(
        {
            "name": "half-pool",
            "policy": "round_robin",
            "zone_policy": "cross_zone",
            "fail_open": False,
            "drain_timeout_ms": 30000,
            "health": desired["target_groups"][0]["health"],
            "targets": [
                {
                    "id": "half-a",
                    "address": "127.0.0.1",
                    "port": 19003,
                    "zone": "zone-a",
                    "administrative_state": "enabled",
                    "weight": 1,
                    "incarnation": 1,
                }
            ],
        }
    )
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, desired, "half.json"), "half-1")[0] in {200, 202}
        wait_active(stack["management"])
        with socket.create_connection(("127.0.0.1", 18003), timeout=5) as client:
            greeting = recv_all(client, 17)
            assert greeting == b"half-close-ready\n"
            client.sendall(b"ack\n")
            client.shutdown(socket.SHUT_WR)
            assert client.recv(4096) == b""


def test_f2p_round_robin_hits_multiple_backends(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "rr-1")[0] in {200, 202}
        wait_active(stack["management"])
        for _ in range(6):
            with socket.create_connection(("127.0.0.1", 18001), timeout=5) as client:
                client.sendall(b"x")
                recv_all(client, 1)
            time.sleep(0.05)
        backends = {event["backend"] for event in lab_events(lab_state) if event.get("event") == "accepted"}
        assert "echo" in backends
        assert "slow" in backends


def test_f2p_source_hash_stable_after_target_reorder(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    desired = scenario_desired()
    desired["target_groups"][1]["targets"].append(
        {
            "id": "inspect-b",
            "address": "127.0.0.1",
            "port": 19001,
            "zone": "zone-a",
            "administrative_state": "enabled",
            "weight": 1,
            "incarnation": 1,
        }
    )
    desired["target_groups"][1]["targets"] = list(reversed(desired["target_groups"][1]["targets"]))
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, desired, "hash.json"), "hash-1")[0] in {200, 202}
        wait_active(stack["management"])
        hits: list[str] = []
        for _ in range(4):
            with socket.create_connection(("127.0.0.1", 18005), timeout=5) as client:
                client.sendall(b"z")
                recv_all(client, 1)
            events = lab_events(lab_state)
            if events:
                hits.append(str(events[-1]["backend"]))
        assert len(set(hits)) == 1


# --- REQ_READINESS ---


def test_f2p_readiness_false_before_activate(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        status, payload = http_json(f"{stack['management']}/ready")
        assert status == 503 or (isinstance(payload, dict) and payload.get("ready") is False)


def test_f2p_readiness_false_during_prepare(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    desired = scenario_desired()
    desired["rollout"]["prepare_quorum"] = 2
    desired["rollout"]["activate_quorum"] = 2
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, desired, "ready-prep.json"), "ready-prep")[0] in {200, 202}
        status, payload = http_json(f"{stack['management']}/ready")
        assert status == 503 or (isinstance(payload, dict) and payload.get("ready") is False)


def test_f2p_readiness_true_after_activate(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "ready-hot")[0] in {200, 202}
        wait_active(stack["management"])
        status, payload = http_json(f"{stack['management']}/ready")
        assert status == 200 and isinstance(payload, dict) and payload.get("ready") is True


# --- REQ_PROTOCOL ---


def test_f2p_unknown_apply_field_rejected(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        body = desired_path(lab_state).read_bytes().decode()
        body = body[:-1] + ',"unexpected":true}'
        status, _payload = http_json(
            f"{stack['management']}/v1/apply",
            method="POST",
            body=body.encode(),
            headers={"Idempotency-Key": "unknown-field"},
        )
        assert status == 400


def test_f2p_metrics_labels_bounded(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        for index in range(5):
            desired = scenario_desired()
            desired["revision"] = index + 1
            apply(stack["management"], write_desired(lab_state, desired, f"metric-{index}.json"), f"metric-{index}")
            time.sleep(0.2)
        metrics = http_text(f"{stack['management']}/metrics")
        generation_labels = [line for line in metrics.splitlines() if "generation=" in line]
        assert len(generation_labels) <= 2


# --- REQ_ELIGIBILITY ---


def test_f2p_same_zone_skips_remote_without_failopen(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    desired = scenario_desired()
    desired["target_groups"][0]["zone_policy"] = "same_zone_preferred"
    desired["target_groups"][0]["fail_open"] = False
    desired["target_groups"][0]["targets"] = [
        {
            "id": "remote-only",
            "address": "127.0.0.1",
            "port": 19002,
            "zone": "zone-b",
            "administrative_state": "enabled",
            "weight": 1,
            "incarnation": 1,
        }
    ]
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, desired, "zone.json"), "zone-1")[0] in {200, 202}
        wait_active(stack["management"])
        expect_no_forwarding("127.0.0.1", 18001)


def test_f2p_fail_open_skips_disabled_targets(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    desired = scenario_desired()
    desired["target_groups"][0]["fail_open"] = True
    desired["target_groups"][0]["targets"] = [
        {
            "id": "disabled-a",
            "address": "127.0.0.1",
            "port": 19001,
            "zone": "zone-a",
            "administrative_state": "disabled",
            "weight": 1,
            "incarnation": 1,
        }
    ]
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, desired, "failopen.json"), "failopen-1")[0] in {200, 202}
        wait_active(stack["management"])
        expect_no_forwarding("127.0.0.1", 18001)


def test_f2p_target_incarnation_increments_on_reregister(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "inc-1")[0] in {200, 202}
        wait_active(stack["management"])
        desired = scenario_desired()
        desired["revision"] = 2
        desired["target_groups"][0]["targets"][0]["incarnation"] = 2
        assert apply(stack["management"], write_desired(lab_state, desired, "inc-2.json"), "inc-2")[0] in {200, 202}
        wait_active(stack["management"])
        gen_dir = control_state / "generations"
        latest = sorted(gen_dir.glob("generation-*"))[-1]
        snapshot = json.loads((latest / "snapshot.json").read_text(encoding="utf-8"))
        incarnation = snapshot["target_groups"][0]["targets"][0]["incarnation"]
        assert incarnation == 2


# --- REQ_RECOVERY ---


def test_f2p_checkpoint_generation_directory_padding(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "ckpt-1")[0] in {200, 202}
        wait_active(stack["management"])
        padded = list(dataplane_state.glob("generation-00000000000000000001"))
        assert padded, f"expected padded checkpoint directory under {dataplane_state}"


def test_f2p_dataplane_restart_recovers_active_generation(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    management_port = free_port()
    control_port = free_port()
    status_port = free_port()
    node_config = write_node_config(dataplane_state, NODE_CONFIG, control_port, status_port)
    env = os.environ.copy()
    env["SOVEREIGN_LB_HOME"] = str(ROOT)
    with managed_process([str(LAB), "start", "--state", str(lab_state)], cwd=ROOT, env=env):
        wait_port("127.0.0.1", 19001, timeout=15)
        with managed_process(
            [str(CONTROL), "-management", f"127.0.0.1:{management_port}", "-control", f"127.0.0.1:{control_port}", "-state", str(control_state)],
            cwd=ROOT,
            env=env,
        ):
            wait_port("127.0.0.1", management_port, timeout=15)
            endpoint = f"http://127.0.0.1:{management_port}"
            proc = subprocess.Popen([str(DATAPLANE), "--config", str(node_config)], cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                wait_port("127.0.0.1", status_port, timeout=15)
                assert apply(endpoint, desired_path(lab_state), "restart-1")[0] in {200, 202}
                wait_active(endpoint)
                proc.kill()
                proc.wait(timeout=5)
                proc = subprocess.Popen([str(DATAPLANE), "--config", str(node_config)], cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                wait_port("127.0.0.1", status_port, timeout=15)
                wait_port("127.0.0.1", 18001, timeout=15)
                with socket.create_connection(("127.0.0.1", 18001), timeout=5) as client:
                    client.sendall(b"ping")
                    assert recv_all(client, 4) == b"ping"
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=3)


def test_f2p_corrupt_current_pointer_falls_back(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "fallback-1")[0] in {200, 202}
        wait_active(stack["management"])
        current = dataplane_state / "CURRENT"
        current.write_text("999999\n", encoding="utf-8")
        status, payload = http_json(f"http://127.0.0.1:{stack['status_port']}/status")
        assert status == 200 and isinstance(payload, dict)
        assert payload.get("active_generation", 0) >= 1
