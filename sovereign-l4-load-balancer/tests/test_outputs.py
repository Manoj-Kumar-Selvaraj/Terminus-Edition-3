"""Behavioral verifier for the sovereign layer-4 load balancer."""

from __future__ import annotations

import hashlib
import json
import errno
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
            with managed_process([str(DATAPLANE), "--config", str(node_config)], cwd=ROOT, env=env):
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


def wait_listener_echo(host: str, port: int, payload: bytes = b"ping", timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2) as client:
                client.settimeout(2.0)
                client.sendall(payload)
                if recv_all(client, len(payload)) == payload:
                    return
        except (OSError, ConnectionError, TimeoutError) as exc:
            last_error = exc
            time.sleep(0.2)
    raise TimeoutError(f"listener {host}:{port} did not recover echo service: {last_error}")


def scenario_least_connections() -> dict[str, Any]:
    desired = scenario_desired()
    group = desired["target_groups"][0]
    group["policy"] = "least_connections"
    group["zone_policy"] = "cross_zone"
    group["fail_open"] = False
    return desired


def scenario_drain_handoff(*, drain_timeout_ms: int = 30000) -> tuple[dict[str, Any], dict[str, Any]]:
    first = scenario_desired()
    first["listeners"] = [first["listeners"][0]]
    first["target_groups"] = [first["target_groups"][0]]
    first["target_groups"][0]["drain_timeout_ms"] = drain_timeout_ms
    first["target_groups"][0]["targets"] = [
        {
            "id": "echo-a",
            "address": "127.0.0.1",
            "port": 19001,
            "zone": "zone-a",
            "administrative_state": "enabled",
            "weight": 1,
            "incarnation": 1,
        }
    ]
    second = json.loads(json.dumps(first))
    second["revision"] = 2
    second["target_groups"][0]["targets"] = [
        {
            "id": "slow-b",
            "address": "127.0.0.1",
            "port": 19002,
            "zone": "zone-a",
            "administrative_state": "enabled",
            "weight": 1,
            "incarnation": 1,
        }
    ]
    return first, second


def reject_candidate_rollout(control_port: int, generation: int, digest: str) -> None:
    """Inject a matching rejected ack so a stuck candidate leaves preparing/activating."""
    with socket.create_connection(("127.0.0.1", control_port), timeout=5) as node:
        node.sendall(encode_control_frame(control_hello("dp-reject", "dp-reject-0001")))
        node.sendall(
            encode_control_frame(
                {
                    "type": "rejected",
                    "node_id": "dp-reject",
                    "session_id": "dp-reject-0001",
                    "sequence": 2,
                    "sent_at": "2026-01-01T00:00:02Z",
                    "generation": generation,
                    "digest": digest,
                    "body": {"reason": "insufficient_quorum"},
                }
            )
        )
        time.sleep(0.2)


def scenario_passive_ejection() -> dict[str, Any]:
    desired = scenario_desired()
    group = desired["target_groups"][0]
    group["policy"] = "round_robin"
    group["zone_policy"] = "cross_zone"
    group["fail_open"] = False
    group["health"]["passive_failures"] = 3
    group["health"]["passive_window_ms"] = 30000
    group["health"]["ejection_ms"] = 30000
    group["targets"] = [
        {
            "id": "reset-a",
            "address": "127.0.0.1",
            "port": 19004,
            "zone": "zone-a",
            "administrative_state": "enabled",
            "weight": 1,
            "incarnation": 1,
        },
        {
            "id": "echo-a",
            "address": "127.0.0.1",
            "port": 19001,
            "zone": "zone-a",
            "administrative_state": "enabled",
            "weight": 1,
            "incarnation": 1,
        },
    ]
    return desired


def lab_events(lab_state: Path) -> list[dict[str, Any]]:
    events_path = lab_state / "events.json"
    if not events_path.is_file():
        return []
    return json.loads(events_path.read_text(encoding="utf-8"))


def recv_exact(connection: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = connection.recv(remaining)
        if not chunk:
            raise ConnectionError("control stream closed early")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def encode_control_frame(envelope: dict[str, Any]) -> bytes:
    body = json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return struct.pack(">I", len(body)) + body


def read_control_frame(connection: socket.socket, timeout: float = 10.0) -> dict[str, Any]:
    connection.settimeout(timeout)
    prefix = recv_exact(connection, 4)
    length = struct.unpack(">I", prefix)[0]
    if length == 0 or length > 4 * 1024 * 1024:
        raise ValueError(f"invalid control frame length {length}")
    payload = recv_exact(connection, length)
    decoded = json.loads(payload.decode("utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def control_hello(node_id: str, session_id: str, sequence: int = 1) -> dict[str, Any]:
    return {
        "type": "hello",
        "node_id": node_id,
        "session_id": session_id,
        "sequence": sequence,
        "sent_at": "2026-01-01T00:00:00Z",
        "body": {
            "capabilities": ["proxy-v2", "checkpoint-v1"],
            "checkpoint_generation": 0,
            "software": "0.1.0",
            "zone": "zone-a",
        },
    }


def wait_rollout_not_active(endpoint: str, timeout: float = 6.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    last: dict[str, Any] = {}
    while time.time() < deadline:
        status, payload = http_json(f"{endpoint}/v1/status")
        assert status == 200 and isinstance(payload, dict)
        last = payload
        if payload.get("rollout", {}).get("phase") == "active" or int(payload.get("active_generation") or 0) > 0:
            pytest.fail("rollout/authority advanced unexpectedly")
        time.sleep(0.25)
    return last


@contextmanager
def hung_backend_port() -> Iterator[int]:
    """Saturate a listen backlog so further outbound connects stall in SYN/connect."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = int(listener.getsockname()[1])
    fillers: list[socket.socket] = []
    stalled = False
    try:
        for _ in range(128):
            candidate = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            candidate.settimeout(0.05)
            try:
                candidate.connect(("127.0.0.1", port))
            except (TimeoutError, socket.timeout):
                candidate.close()
                stalled = True
                break
            except OSError:
                candidate.close()
                stalled = True
                break
            fillers.append(candidate)
        if not stalled:
            # Last attempt: nonblocking connect should report EINPROGRESS when full.
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            probe.setblocking(False)
            result = probe.connect_ex(("127.0.0.1", port))
            fillers.append(probe)
            stalled = result in {0, errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EAGAIN} and result != 0
        if not stalled:
            listener.close()
            for filler in fillers:
                try:
                    filler.close()
                except OSError:
                    pass
            raise RuntimeError("unable to create a stalled connect target on loopback")
        yield port
    finally:
        for filler in fillers:
            try:
                filler.close()
            except OSError:
                pass
        try:
            listener.close()
        except OSError:
            pass


def scenario_active_health_fail() -> dict[str, Any]:
    desired = scenario_desired()
    group = desired["target_groups"][0]
    group["policy"] = "round_robin"
    group["zone_policy"] = "cross_zone"
    group["fail_open"] = False
    group["health"] = {
        "interval_ms": 200,
        "timeout_ms": 100,
        "healthy_threshold": 2,
        "unhealthy_threshold": 2,
        "passive_failures": 3,
        "passive_window_ms": 10000,
        "ejection_ms": 15000,
        "send": "PING\n",
        "expect": "PONG\n",
    }
    group["targets"] = [
        {
            "id": "echo-a",
            "address": "127.0.0.1",
            "port": 19001,
            "zone": "zone-a",
            "administrative_state": "enabled",
            "weight": 1,
            "incarnation": 1,
        }
    ]
    desired["listeners"] = [desired["listeners"][0]]
    desired["target_groups"] = [group]
    return desired


def scenario_active_health_recover(base: dict[str, Any]) -> dict[str, Any]:
    recovered = json.loads(json.dumps(base))
    recovered["revision"] = int(base["revision"]) + 1
    recovered["target_groups"][0]["health"]["send"] = "PING\n"
    recovered["target_groups"][0]["health"]["expect"] = "PING\n"
    return recovered


# --- P2P smoke ---


def test_p2p_binaries_and_catalog_present() -> None:
    assert CONTROL.is_file()
    assert DATAPLANE.is_file()
    assert LBCTL.is_file()
    assert SCENARIO.is_file()
    fleet_path = ROOT / "config" / "fleet.json"
    assert fleet_path.is_file()
    fleet = json.loads(fleet_path.read_text(encoding="utf-8"))
    nodes = fleet.get("nodes")
    assert isinstance(nodes, list) and len(nodes) == 24
    zones = {str(node.get("zone")) for node in nodes if isinstance(node, dict)}
    assert zones == {"zone-a", "zone-b", "zone-c"}


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


def test_f2p_failed_candidate_preserves_lkg_generation(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    """Active generation N must keep serving when a later accepted candidate cannot reach quorum; next apply must not reuse the failed generation id."""
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        first_status, first_payload = apply(stack["management"], desired_path(lab_state), "lkg-1")
        assert first_status in {200, 202}
        wait_active(stack["management"])
        active_before = int(first_payload["generation"])
        _, before = http_json(f"{stack['management']}/v1/status")
        assert isinstance(before, dict)
        assert int(before.get("active_generation") or 0) == active_before
        wait_listener_echo("127.0.0.1", 18001)

        candidate = scenario_desired()
        candidate["revision"] = 2
        candidate["listeners"][0]["idle_timeout_ms"] = 33000
        candidate["rollout"]["prepare_quorum"] = 2
        candidate["rollout"]["activate_quorum"] = 2
        candidate["rollout"]["prepare_timeout_ms"] = 2000
        candidate["rollout"]["activate_timeout_ms"] = 2000
        cand_status, cand_payload = apply(
            stack["management"], write_desired(lab_state, candidate, "lkg-candidate.json"), "lkg-2"
        )
        assert cand_status in {200, 202}
        failed_generation = int(cand_payload["generation"])
        failed_digest = str(cand_payload["digest"])
        assert failed_generation > active_before

        deadline = time.time() + 6
        while time.time() < deadline:
            _status, body = http_json(f"{stack['management']}/v1/status")
            assert isinstance(body, dict)
            assert int(body.get("active_generation") or 0) == active_before
            if body.get("rollout", {}).get("phase") == "active" and int(body.get("active_generation") or 0) == failed_generation:
                pytest.fail("failed candidate must not become the active generation")
            time.sleep(0.25)
        wait_listener_echo("127.0.0.1", 18001)

        reject_candidate_rollout(stack["control_port"], failed_generation, failed_digest)
        recovery = scenario_desired()
        recovery["revision"] = 3
        recovery["listeners"][0]["idle_timeout_ms"] = 34000
        recovery["rollout"]["prepare_quorum"] = 1
        recovery["rollout"]["activate_quorum"] = 1
        next_status, next_payload = apply(
            stack["management"], write_desired(lab_state, recovery, "lkg-recovery.json"), "lkg-3"
        )
        assert next_status in {200, 202}
        next_generation = int(next_payload["generation"])
        assert next_generation > failed_generation
        assert next_generation != failed_generation
        wait_active(stack["management"])
        _, after = http_json(f"{stack['management']}/v1/status")
        assert isinstance(after, dict)
        assert int(after.get("active_generation") or 0) == next_generation


def test_f2p_status_reports_rollout_present(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "status-rollout")[0] in {200, 202}
        status, payload = http_json(f"{stack['management']}/v1/status")
        assert status == 200 and isinstance(payload, dict)
        assert payload.get("rollout_present") is True


def test_f2p_audit_exports_bounded_apply_event(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "audit-1")[0] in {200, 202}
        status, payload = http_json(f"{stack['management']}/v1/audit")
        assert status == 200 and isinstance(payload, dict)
        events = payload.get("events")
        assert isinstance(events, list) and events
        event = events[-1]
        assert event.get("operation") == "apply"
        assert event.get("outcome") == "accepted"
        assert "revision" in event and "generation" in event
        forbidden = {"payload", "body", "source_address", "client_address", "idempotency_key"}
        assert forbidden.isdisjoint(event.keys())


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
        marker = time.time_ns()
        with socket.create_connection(("127.0.0.1", 18005), timeout=5) as client:
            client.settimeout(5.0)
            client.sendall(b"probe\n")
            assert recv_all(client, 6) == b"probe\n"
            client.sendall(b"again\n")
            assert recv_all(client, 6) == b"again\n"
        deadline = time.time() + 3.0
        headers: list[dict[str, Any]] = []
        repeats: list[dict[str, Any]] = []
        while time.time() < deadline:
            events = [event for event in lab_events(lab_state) if event.get("at_ns", 0) >= marker]
            headers = [event for event in events if event.get("event") == "proxy_header"]
            repeats = [event for event in events if event.get("event") == "proxy_header_repeat"]
            if headers:
                break
            time.sleep(0.1)
        assert len(headers) == 1, "exactly one PROXY v2 header on first backend establish"
        assert headers[0].get("count") == 1
        assert repeats == [], "no second PROXY header on the same established backend"


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
    """Round-robin must rotate across eligible targets; use cross_zone so both stock backends are selectable."""
    desired = scenario_desired()
    desired["target_groups"][0]["zone_policy"] = "cross_zone"
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, desired, "rr.json"), "rr-1")[0] in {200, 202}
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


def test_f2p_least_connections_prefers_lower_load(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    warm = scenario_least_connections()
    warm["target_groups"][0]["targets"] = [
        {
            "id": "slow-b",
            "address": "127.0.0.1",
            "port": 19002,
            "zone": "zone-a",
            "administrative_state": "enabled",
            "weight": 1,
            "incarnation": 1,
        }
    ]
    hot = scenario_least_connections()
    hot["revision"] = 2
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, warm, "lc-warm.json"), "lc-warm")[0] in {200, 202}
        wait_active(stack["management"])
        slow_sock = socket.create_connection(("127.0.0.1", 18001), timeout=5)
        try:
            slow_sock.sendall(b"x" * 512)
            time.sleep(0.2)
            assert apply(stack["management"], write_desired(lab_state, hot, "lc-hot.json"), "lc-hot")[0] in {200, 202}
            wait_active(stack["management"])
            with socket.create_connection(("127.0.0.1", 18001), timeout=5) as quick:
                quick.sendall(b"y")
                recv_all(quick, 1)
            accepted = [event for event in lab_events(lab_state) if event.get("event") == "accepted"]
            assert accepted and accepted[-1]["backend"] == "echo"
        finally:
            slow_sock.close()


def test_f2p_connect_timeout_closes_stalled_backend(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with hung_backend_port() as hung_port:
        desired = scenario_desired()
        desired["listeners"] = [
            {
                "name": "echo",
                "address": "127.0.0.1",
                "port": 18001,
                "target_group": "echo-pool",
                "proxy_protocol_v2": False,
                "connect_timeout_ms": 400,
                "idle_timeout_ms": 30000,
                "buffer_bytes": 65536,
            }
        ]
        desired["target_groups"] = [
            {
                "name": "echo-pool",
                "policy": "round_robin",
                "zone_policy": "cross_zone",
                "fail_open": False,
                "drain_timeout_ms": 30000,
                "health": {
                    "interval_ms": 5000,
                    "timeout_ms": 500,
                    "healthy_threshold": 2,
                    "unhealthy_threshold": 3,
                    "passive_failures": 3,
                    "passive_window_ms": 10000,
                    "ejection_ms": 15000,
                },
                "targets": [
                    {
                        "id": "hung-a",
                        "address": "127.0.0.1",
                        "port": hung_port,
                        "zone": "zone-a",
                        "administrative_state": "enabled",
                        "weight": 1,
                        "incarnation": 1,
                    }
                ],
            }
        ]
        with running_stack(lab_state, control_state, dataplane_state) as stack:
            assert apply(stack["management"], write_desired(lab_state, desired, "connect-timeout.json"), "connect-timeout")[0] in {
                200,
                202,
            }
            wait_active(stack["management"])
            started = time.time()
            with socket.create_connection(("127.0.0.1", 18001), timeout=5) as client:
                client.settimeout(3.0)
                try:
                    client.sendall(b"x")
                except OSError:
                    pass
                data = b""
                try:
                    data = client.recv(16)
                except (TimeoutError, socket.timeout, ConnectionResetError, OSError):
                    data = b""
            elapsed = time.time() - started
            assert data == b""
            assert elapsed < 2.5, f"connect timeout did not tear down promptly ({elapsed:.2f}s)"


def test_f2p_idle_timeout_tears_down_quiet_stream(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    desired = scenario_desired()
    desired["listeners"][0]["idle_timeout_ms"] = 700
    desired["listeners"] = [desired["listeners"][0]]
    desired["target_groups"] = [desired["target_groups"][0]]
    desired["target_groups"][0]["targets"] = [
        {
            "id": "echo-a",
            "address": "127.0.0.1",
            "port": 19001,
            "zone": "zone-a",
            "administrative_state": "enabled",
            "weight": 1,
            "incarnation": 1,
        }
    ]
    desired["target_groups"][0]["fail_open"] = False
    desired["target_groups"][0]["zone_policy"] = "cross_zone"
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, desired, "idle-timeout.json"), "idle-timeout")[0] in {200, 202}
        wait_active(stack["management"])
        with socket.create_connection(("127.0.0.1", 18001), timeout=5) as client:
            client.settimeout(3.0)
            client.sendall(b"hi")
            assert recv_all(client, 2) == b"hi"
            started = time.time()
            data = b"sentinel"
            try:
                data = client.recv(16)
            except (TimeoutError, socket.timeout):
                data = b"timeout"
            except (ConnectionResetError, OSError):
                data = b""
            elapsed = time.time() - started
            assert data == b"", f"idle timeout should close quietly, got {data!r}"
            assert elapsed < 2.5


def test_f2p_slow_backend_survives_full_buffer_backpressure(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    desired = scenario_desired()
    desired["listeners"] = [
        {
            "name": "echo",
            "address": "127.0.0.1",
            "port": 18001,
            "target_group": "echo-pool",
            "proxy_protocol_v2": False,
            "connect_timeout_ms": 1000,
            "idle_timeout_ms": 30000,
            "buffer_bytes": 4096,
        }
    ]
    desired["target_groups"] = [
        {
            "name": "echo-pool",
            "policy": "round_robin",
            "zone_policy": "cross_zone",
            "fail_open": False,
            "drain_timeout_ms": 30000,
            "health": desired["target_groups"][0]["health"],
            "targets": [
                {
                    "id": "slow-b",
                    "address": "127.0.0.1",
                    "port": 19002,
                    "zone": "zone-a",
                    "administrative_state": "enabled",
                    "weight": 1,
                    "incarnation": 1,
                }
            ],
        }
    ]
    payload = b"B" * 16384
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, desired, "backpressure.json"), "backpressure")[0] in {200, 202}
        wait_active(stack["management"])
        with socket.create_connection(("127.0.0.1", 18001), timeout=5) as client:
            client.settimeout(20.0)
            offset = 0
            while offset < len(payload):
                sent = client.send(payload[offset : offset + 1024])
                assert sent > 0
                offset += sent
            client.shutdown(socket.SHUT_WR)
            assert recv_all(client, len(payload)) == payload


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
        dp_status, dp_payload = http_json(f"http://127.0.0.1:{stack['status_port']}/status")
        assert dp_status == 200 and isinstance(dp_payload, dict)
        assert isinstance(dp_payload.get("connections"), int)
        assert dp_payload.get("connections", -1) >= 0


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
        assert generation_labels == [], "metrics must not attach generation= labels"


def test_f2p_torn_control_frame_does_not_advance_authority(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    """Torn length-prefix/body on the control channel must not count toward quorum."""
    del dataplane_state  # control-plane-only probe
    management_port = free_port()
    control_port = free_port()
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
            with socket.create_connection(("127.0.0.1", control_port), timeout=5) as node:
                node.sendall(encode_control_frame(control_hello("dp-probe", "dp-probe-0001")))
                assert apply(endpoint, desired_path(lab_state), "torn-frame")[0] in {200, 202}
                prepare = read_control_frame(node, timeout=10.0)
                assert prepare.get("type") == "prepare"
                # Announce a body length then close before delivering it.
                node.sendall(struct.pack(">I", 64))
                node.sendall(b'{"type":"prepared"')
            wait_rollout_not_active(endpoint, timeout=5.0)
            authority = json.loads((control_state / "authority.json").read_text(encoding="utf-8"))
            assert int(authority.get("accepted_revision") or 0) == 1
            status, payload = http_json(f"{endpoint}/v1/status")
            assert status == 200 and isinstance(payload, dict)
            assert int(payload.get("active_generation") or 0) == 0
            assert payload.get("rollout", {}).get("phase") != "active"


def test_f2p_control_session_sequence_mismatch_rejected(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    """Stale session or sequence reuse must not progress prepare/activate quorum."""
    del dataplane_state
    management_port = free_port()
    control_port = free_port()
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
            with socket.create_connection(("127.0.0.1", control_port), timeout=5) as node:
                node.sendall(encode_control_frame(control_hello("dp-probe", "dp-probe-0001")))
                assert apply(endpoint, desired_path(lab_state), "fence-session")[0] in {200, 202}
                prepare = read_control_frame(node, timeout=10.0)
                assert prepare.get("type") == "prepare"
                bad_session = {
                    "type": "prepared",
                    "node_id": "dp-probe",
                    "session_id": "dp-probe-stale",
                    "sequence": 2,
                    "sent_at": "2026-01-01T00:00:02Z",
                    "generation": prepare["generation"],
                    "digest": prepare["digest"],
                    "body": {},
                }
                node.sendall(encode_control_frame(bad_session))
            wait_rollout_not_active(endpoint, timeout=4.0)

            high_quorum = scenario_desired()
            high_quorum["revision"] = 2
            high_quorum["rollout"]["prepare_quorum"] = 2
            high_quorum["rollout"]["activate_quorum"] = 2
            with socket.create_connection(("127.0.0.1", control_port), timeout=5) as node:
                node.sendall(encode_control_frame(control_hello("dp-probe", "dp-probe-0002", sequence=1)))
                assert apply(endpoint, write_desired(lab_state, high_quorum, "fence-seq.json"), "fence-seq")[0] in {200, 202}
                prepare = read_control_frame(node, timeout=10.0)
                assert prepare.get("type") == "prepare"
                first = {
                    "type": "prepared",
                    "node_id": "dp-probe",
                    "session_id": "dp-probe-0002",
                    "sequence": 2,
                    "sent_at": "2026-01-01T00:00:03Z",
                    "generation": prepare["generation"],
                    "digest": prepare["digest"],
                    "body": {},
                }
                node.sendall(encode_control_frame(first))
                # Reuse sequence with different content — must not satisfy quorum.
                reused = dict(first)
                reused["body"] = {"detail": "different"}
                reused["sent_at"] = "2026-01-01T00:00:04Z"
                try:
                    node.sendall(encode_control_frame(reused))
                except OSError:
                    pass
            wait_rollout_not_active(endpoint, timeout=4.0)


def test_f2p_control_status_envelope_exchange(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    """Bidirectional control status must return a bounded status body and must not advance authority alone."""
    del lab_state, control_state
    control_port = free_port()
    status_port = free_port()
    node_config = write_node_config(dataplane_state, NODE_CONFIG, control_port, status_port)
    env = os.environ.copy()
    env["SOVEREIGN_LB_HOME"] = str(ROOT)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", control_port))
    listener.listen(1)
    listener.settimeout(15.0)
    try:
        with managed_process([str(DATAPLANE), "--config", str(node_config)], cwd=ROOT, env=env):
            wait_port("127.0.0.1", status_port, timeout=15)
            connection, _peer = listener.accept()
            with connection:
                hello = read_control_frame(connection, timeout=10.0)
                assert hello.get("type") == "hello"
                node_id = str(hello["node_id"])
                session_id = str(hello["session_id"])
                status_request = {
                    "type": "status",
                    "node_id": node_id,
                    "session_id": session_id,
                    "sequence": 2,
                    "sent_at": "2026-01-01T00:00:01Z",
                    "body": {},
                }
                connection.sendall(encode_control_frame(status_request))
                status_reply = read_control_frame(connection, timeout=10.0)
                assert status_reply.get("type") == "status"
                assert status_reply.get("node_id") == node_id
                assert status_reply.get("session_id") == session_id
                assert int(status_reply.get("sequence") or 0) > int(hello.get("sequence") or 0)
                body = status_reply.get("body")
                assert isinstance(body, dict)
                assert "ready" in body
                assert "active_generation" in body
                assert "connections" in body
                assert isinstance(body.get("ready"), bool)
                assert isinstance(body.get("active_generation"), int)
                assert isinstance(body.get("connections"), int)
                assert int(body["connections"]) >= 0
                # Status alone must not publish listeners or invent an active generation.
                assert int(body["active_generation"]) == 0
                assert body.get("ready") is False
                http_status, http_body = http_json(f"http://127.0.0.1:{status_port}/status")
                assert http_status == 200 and isinstance(http_body, dict)
                assert int(http_body.get("active_generation") or 0) == 0
    finally:
        listener.close()


# --- REQ_ELIGIBILITY ---


def test_f2p_same_zone_skips_remote_without_failopen(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    """same_zone_preferred + fail_open=false with only remote-zone targets must not soft-fallback."""
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


def test_f2p_fail_open_includes_unhealthy_targets(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    """With fail_open=true, unhealthy-only pools must keep forwarding (unlike fail_open=false)."""
    desired = scenario_active_health_fail()
    desired["target_groups"][0]["fail_open"] = True
    desired["target_groups"][0]["zone_policy"] = "same_zone_preferred"
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, desired, "failopen-unhealthy.json"), "failopen-unhealthy")[0] in {
            200,
            202,
        }
        wait_active(stack["management"])
        # Allow active probes to cross unhealthy_threshold; fail-open must still select the target.
        time.sleep(2.0)
        recovered = False
        deadline = time.time() + 6.0
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", 18001), timeout=2) as client:
                    client.settimeout(2.0)
                    client.sendall(b"ok")
                    if recv_all(client, 2) == b"ok":
                        recovered = True
                        break
            except (OSError, ConnectionError, TimeoutError):
                time.sleep(0.3)
        assert recovered, "fail_open=true must continue forwarding when only unhealthy targets remain"


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


def test_f2p_deregistered_target_drains_existing_connection(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    first, second = scenario_drain_handoff(drain_timeout_ms=30000)
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, first, "drain-1.json"), "drain-1")[0] in {200, 202}
        wait_active(stack["management"])
        hold = socket.create_connection(("127.0.0.1", 18001), timeout=5)
        try:
            hold.sendall(b"keep")
            assert recv_all(hold, 4) == b"keep"
            assert apply(stack["management"], write_desired(lab_state, second, "drain-2.json"), "drain-2")[0] in {200, 202}
            wait_active(stack["management"])
            marker = time.time_ns()
            with socket.create_connection(("127.0.0.1", 18001), timeout=5) as client:
                client.sendall(b"new")
                recv_all(client, 3)
            accepted = [
                event
                for event in lab_events(lab_state)
                if event.get("event") == "accepted"
                and event.get("backend") in {"echo", "slow"}
                and event.get("at_ns", 0) >= marker
            ]
            assert accepted and accepted[-1]["backend"] == "slow"
            hold.sendall(b"more")
            assert recv_all(hold, 4) == b"more"
        finally:
            hold.close()


def test_f2p_drain_deadline_terminates_owned_stream(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    """Owned streams on a deregistered target must be force-closed once drain_timeout_ms elapses."""
    first, second = scenario_drain_handoff(drain_timeout_ms=800)
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, first, "drain-deadline-1.json"), "drain-deadline-1")[0] in {
            200,
            202,
        }
        wait_active(stack["management"])
        hold = socket.create_connection(("127.0.0.1", 18001), timeout=5)
        try:
            hold.settimeout(2.0)
            hold.sendall(b"keep")
            assert recv_all(hold, 4) == b"keep"
            assert apply(
                stack["management"], write_desired(lab_state, second, "drain-deadline-2.json"), "drain-deadline-2"
            )[0] in {200, 202}
            wait_active(stack["management"])
            hold.sendall(b"still")
            assert recv_all(hold, 5) == b"still"
            deadline = time.time() + 3.0
            closed = False
            while time.time() < deadline:
                try:
                    hold.sendall(b"x")
                    chunk = hold.recv(1)
                    if chunk == b"":
                        closed = True
                        break
                except (ConnectionError, TimeoutError, OSError, BrokenPipeError):
                    closed = True
                    break
                time.sleep(0.1)
            assert closed, "drain deadline must terminate the owned stream"
        finally:
            hold.close()


def test_f2p_passive_ejection_skips_reset_target(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    reset_only = scenario_passive_ejection()
    reset_only["target_groups"][0]["health"]["passive_failures"] = 1
    reset_only["target_groups"][0]["targets"] = [
        {
            "id": "reset-a",
            "address": "127.0.0.1",
            "port": 19004,
            "zone": "zone-a",
            "administrative_state": "enabled",
            "weight": 1,
            "incarnation": 1,
        }
    ]
    echo_only = scenario_passive_ejection()
    echo_only["revision"] = 2
    echo_only["target_groups"][0]["health"]["passive_failures"] = 1
    echo_only["target_groups"][0]["targets"] = [
        {
            "id": "echo-a",
            "address": "127.0.0.1",
            "port": 19001,
            "zone": "zone-a",
            "administrative_state": "enabled",
            "weight": 1,
            "incarnation": 1,
        }
    ]
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, reset_only, "passive-reset.json"), "passive-reset")[0] in {200, 202}
        wait_active(stack["management"])
        for _ in range(4):
            try:
                with socket.create_connection(("127.0.0.1", 18001), timeout=2) as client:
                    client.settimeout(1.0)
                    client.sendall(b"x")
                    try:
                        recv_all(client, 1)
                    except (ConnectionResetError, TimeoutError, OSError):
                        pass
            except OSError:
                pass
            time.sleep(0.15)
        marker = time.time_ns()
        for _ in range(3):
            try:
                with socket.create_connection(("127.0.0.1", 18001), timeout=2) as client:
                    client.settimeout(1.0)
                    client.sendall(b"probe")
                    recv_all(client, 1)
            except (ConnectionResetError, TimeoutError, OSError):
                pass
            time.sleep(0.1)
        reset_after_ejection = [
            event
            for event in lab_events(lab_state)
            if event.get("event") == "accepted"
            and event.get("backend") == "reset"
            and event.get("at_ns", 0) >= marker
        ]
        assert not reset_after_ejection, "passive ejection should stop routing to reset"
        assert apply(stack["management"], write_desired(lab_state, echo_only, "passive-echo.json"), "passive-echo")[0] in {200, 202}
        wait_active(stack["management"])
        with socket.create_connection(("127.0.0.1", 18001), timeout=5) as client:
            client.sendall(b"ok")
            assert recv_all(client, 2) == b"ok"
        accepted = [
            event
            for event in lab_events(lab_state)
            if event.get("event") == "accepted"
            and event.get("backend") == "echo"
            and event.get("at_ns", 0) >= marker
        ]
        assert accepted


def test_f2p_active_health_failure_skips_then_recovers(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    failing = scenario_active_health_fail()
    recovering = scenario_active_health_recover(failing)
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], write_desired(lab_state, failing, "active-fail.json"), "active-fail")[0] in {200, 202}
        wait_active(stack["management"])
        deadline = time.time() + 8.0
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", 18001), timeout=1) as client:
                    client.settimeout(0.5)
                    client.sendall(b"probe")
                    echoed = recv_all(client, 1)
                    if echoed:
                        time.sleep(0.3)
                        continue
            except (OSError, ConnectionError, TimeoutError):
                pass
            # Sustained skip after unhealthy_threshold probe failures.
            expect_no_forwarding("127.0.0.1", 18001)
            break
        else:
            pytest.fail("active health failure should skip the target under fail_open=false")

        assert apply(stack["management"], write_desired(lab_state, recovering, "active-recover.json"), "active-recover")[0] in {
            200,
            202,
        }
        wait_active(stack["management"])
        recovered = False
        recover_deadline = time.time() + 8.0
        while time.time() < recover_deadline:
            try:
                with socket.create_connection(("127.0.0.1", 18001), timeout=2) as client:
                    client.settimeout(2.0)
                    client.sendall(b"ok")
                    if recv_all(client, 2) == b"ok":
                        recovered = True
                        break
            except (OSError, ConnectionError, TimeoutError):
                time.sleep(0.3)
        assert recovered, "target should become eligible again after healthy_threshold successes"


# --- REQ_RECOVERY ---


def test_f2p_checkpoint_generation_directory_padding(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    with running_stack(lab_state, control_state, dataplane_state) as stack:
        assert apply(stack["management"], desired_path(lab_state), "ckpt-1")[0] in {200, 202}
        wait_active(stack["management"])
        padded = list(dataplane_state.glob("generation-00000000000000000001"))
        assert padded, f"expected padded checkpoint directory under {dataplane_state}"


def test_f2p_dataplane_restart_recovers_active_generation(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    """Checkpoint recovery must restore listeners without a fresh control-plane republish."""
    management_port = free_port()
    control_port = free_port()
    status_port = free_port()
    node_config = write_node_config(dataplane_state, NODE_CONFIG, control_port, status_port)
    env = os.environ.copy()
    env["SOVEREIGN_LB_HOME"] = str(ROOT)
    with managed_process([str(LAB), "start", "--state", str(lab_state)], cwd=ROOT, env=env):
        wait_port("127.0.0.1", 19001, timeout=15)
        control = subprocess.Popen(
            [str(CONTROL), "-management", f"127.0.0.1:{management_port}", "-control", f"127.0.0.1:{control_port}", "-state", str(control_state)],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        dataplane: subprocess.Popen[str] | None = None
        stopped_control = False
        try:
            wait_port("127.0.0.1", management_port, timeout=15)
            endpoint = f"http://127.0.0.1:{management_port}"
            dataplane = subprocess.Popen(
                [str(DATAPLANE), "--config", str(node_config)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            wait_port("127.0.0.1", status_port, timeout=15)
            assert apply(endpoint, desired_path(lab_state), "restart-1")[0] in {200, 202}
            wait_active(endpoint)
            assert list(dataplane_state.glob("generation-*")), "expected a verified dataplane checkpoint before restart"

            # Stop control first so reconnect cannot re-prepare/activate and mask checkpoint load.
            control.terminate()
            try:
                control.wait(timeout=5)
            except subprocess.TimeoutExpired:
                control.kill()
                control.wait(timeout=2)
            stopped_control = True

            assert dataplane is not None
            dataplane.kill()
            dataplane.wait(timeout=5)
            dataplane = subprocess.Popen(
                [str(DATAPLANE), "--config", str(node_config)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            wait_port("127.0.0.1", status_port, timeout=15)
            status, payload = http_json(f"http://127.0.0.1:{status_port}/status")
            assert status == 200 and isinstance(payload, dict)
            assert payload.get("ready") is True
            assert int(payload.get("active_generation") or 0) >= 1
            assert int(payload.get("listener_count") or 0) >= 1
            wait_listener_echo("127.0.0.1", 18001)
        finally:
            if dataplane is not None and dataplane.poll() is None:
                dataplane.kill()
                dataplane.wait(timeout=3)
            if not stopped_control and control.poll() is None:
                control.kill()
                control.wait(timeout=3)


def test_f2p_corrupt_current_pointer_falls_back(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    """Corrupt CURRENT must fall back to the highest verified generation after dataplane reload."""
    management_port = free_port()
    control_port = free_port()
    status_port = free_port()
    node_config = write_node_config(dataplane_state, NODE_CONFIG, control_port, status_port)
    env = os.environ.copy()
    env["SOVEREIGN_LB_HOME"] = str(ROOT)
    with managed_process([str(LAB), "start", "--state", str(lab_state)], cwd=ROOT, env=env):
        wait_port("127.0.0.1", 19001, timeout=15)
        control = subprocess.Popen(
            [str(CONTROL), "-management", f"127.0.0.1:{management_port}", "-control", f"127.0.0.1:{control_port}", "-state", str(control_state)],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        dataplane: subprocess.Popen[str] | None = None
        stopped_control = False
        try:
            wait_port("127.0.0.1", management_port, timeout=15)
            endpoint = f"http://127.0.0.1:{management_port}"
            dataplane = subprocess.Popen(
                [str(DATAPLANE), "--config", str(node_config)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            wait_port("127.0.0.1", status_port, timeout=15)
            assert apply(endpoint, desired_path(lab_state), "fallback-1")[0] in {200, 202}
            wait_active(endpoint)
            assert list(dataplane_state.glob("generation-*")), "expected verified generation content before CURRENT corruption"

            current = dataplane_state / "CURRENT"
            current.write_text("999999\n", encoding="utf-8")

            # Isolate from control republish and force startup CURRENT fallback.
            control.terminate()
            try:
                control.wait(timeout=5)
            except subprocess.TimeoutExpired:
                control.kill()
                control.wait(timeout=2)
            stopped_control = True

            assert dataplane is not None
            dataplane.kill()
            dataplane.wait(timeout=5)
            dataplane = subprocess.Popen(
                [str(DATAPLANE), "--config", str(node_config)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            wait_port("127.0.0.1", status_port, timeout=15)
            status, payload = http_json(f"http://127.0.0.1:{status_port}/status")
            assert status == 200 and isinstance(payload, dict)
            assert payload.get("ready") is True
            assert int(payload.get("active_generation") or 0) >= 1
            assert int(payload.get("listener_count") or 0) >= 1
            wait_listener_echo("127.0.0.1", 18001)
        finally:
            if dataplane is not None and dataplane.poll() is None:
                dataplane.kill()
                dataplane.wait(timeout=3)
            if not stopped_control and control.poll() is None:
                control.kill()
                control.wait(timeout=3)


def test_f2p_control_plane_restart_restores_authority_fences(lab_state: Path, control_state: Path, dataplane_state: Path) -> None:
    management_port = free_port()
    control_port = free_port()
    status_port = free_port()
    node_config = write_node_config(dataplane_state, NODE_CONFIG, control_port, status_port)
    env = os.environ.copy()
    env["SOVEREIGN_LB_HOME"] = str(ROOT)
    with managed_process([str(LAB), "start", "--state", str(lab_state)], cwd=ROOT, env=env):
        wait_port("127.0.0.1", 19001, timeout=15)
        control = subprocess.Popen(
            [str(CONTROL), "-management", f"127.0.0.1:{management_port}", "-control", f"127.0.0.1:{control_port}", "-state", str(control_state)],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            wait_port("127.0.0.1", management_port, timeout=15)
            with managed_process([str(DATAPLANE), "--config", str(node_config)], cwd=ROOT, env=env):
                wait_port("127.0.0.1", status_port, timeout=15)
                endpoint = f"http://127.0.0.1:{management_port}"
                first = apply(endpoint, desired_path(lab_state), "cp-restart-1")
                assert first[0] in {200, 202}
                wait_active(endpoint)
                authority_before = json.loads((control_state / "authority.json").read_text(encoding="utf-8"))
                accepted_revision = int(authority_before["accepted_revision"])
                accepted_digest = str(authority_before.get("accepted_digest") or "")
                assert accepted_revision == 1
                assert len(accepted_digest) == 64
                generation = first[1]["generation"]

                control.terminate()
                try:
                    control.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    control.kill()
                    control.wait(timeout=2)
                time.sleep(0.3)

                management_port = free_port()
                control = subprocess.Popen(
                    [str(CONTROL), "-management", f"127.0.0.1:{management_port}", "-control", f"127.0.0.1:{control_port}", "-state", str(control_state)],
                    cwd=str(ROOT),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                wait_port("127.0.0.1", management_port, timeout=15)
                endpoint = f"http://127.0.0.1:{management_port}"

                status, payload = http_json(f"{endpoint}/v1/status")
                assert status == 200 and isinstance(payload, dict)
                assert payload["accepted_revision"] == accepted_revision
                authority_after = json.loads((control_state / "authority.json").read_text(encoding="utf-8"))
                assert authority_after.get("accepted_digest") == accepted_digest

                replay = apply(endpoint, desired_path(lab_state), "cp-restart-1")
                assert replay[0] == 200
                assert replay[1]["generation"] == generation

                stale = scenario_desired()
                stale["revision"] = 1
                stale_status, _payload = apply(endpoint, write_desired(lab_state, stale, "cp-stale.json"), "cp-stale")
                assert stale_status == 409
        finally:
            if control.poll() is None:
                control.terminate()
                try:
                    control.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    control.kill()
                    control.wait(timeout=2)