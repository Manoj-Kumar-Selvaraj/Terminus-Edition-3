"""Behavioral verifier for the Jenkins Operational Insights plugin core."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pytest


PLUGIN = Path("/app/plugin")
BUILD_CORE = PLUGIN / "bin" / "build-core"
INSIGHTS = PLUGIN / "bin" / "insights"
BASE_TIME = 1_735_689_600_000


def run_process(
    arguments: list[str],
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        arguments,
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    if check and completed.returncode != 0:
        pytest.fail(
            f"command failed ({completed.returncode}): {' '.join(arguments)}\n"
            f"stdout: {completed.stdout}\nstderr: {completed.stderr}"
        )
    return completed


def run_cli(
    home: Path,
    state: Path,
    command: str,
    *options: str,
    check: bool = True,
    env: dict[str, str] | None = None,
    timeout: int = 120,
) -> dict[str, Any] | subprocess.CompletedProcess[str]:
    completed = run_process(
        [
            "sh",
            str(INSIGHTS),
            command,
            "--home",
            str(home),
            "--state",
            str(state),
            *options,
        ],
        check=check,
        env=env,
        timeout=timeout,
    )
    if not check:
        return completed
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        pytest.fail(f"CLI did not emit one JSON object: {completed.stdout!r}: {error}")


def generate(home: Path, records: int = 10_000, seed: int = 731_927) -> dict[str, Any]:
    completed = run_process(
        [
            "sh",
            str(INSIGHTS),
            "generate",
            "--home",
            str(home),
            "--records",
            str(records),
            "--seed",
            str(seed),
        ],
        timeout=300,
    )
    return json.loads(completed.stdout)


def response(value: dict[str, Any]) -> dict[str, Any]:
    return value.get("response", value)


def query(home: Path, state: Path, *options: str) -> dict[str, Any]:
    return response(run_cli(home, state, "query", *options))


def write_rows(path: Path, rows: list[dict[str, Any] | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(row if isinstance(row, str) else json.dumps(row, separators=(",", ":"), sort_keys=True))
            stream.write("\n")


def make_home(
    root: Path,
    *,
    jobs: list[dict[str, Any] | str] | None = None,
    builds: list[dict[str, Any] | str] | None = None,
    queue: list[dict[str, Any] | str] | None = None,
    nodes: list[dict[str, Any] | str] | None = None,
    fingerprints: list[dict[str, Any] | str] | None = None,
    plugins: list[dict[str, Any] | str] | None = None,
    fingerprint_enumeration: bool = True,
) -> Path:
    exports = root / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    families = {
        "jobs": jobs or [],
        "builds": builds or [],
        "queue": queue or [],
        "nodes": nodes or [],
        "fingerprints": fingerprints or [],
        "plugins": plugins or [],
    }
    for name, rows in families.items():
        write_rows(exports / f"{name}.ndjson", rows)
    (exports / "fingerprint-capability.json").write_text(
        json.dumps({"enumeration": fingerprint_enumeration, "provider": "verifier"}),
        encoding="utf-8",
    )
    return root


def job(key: str, full_name: str | None = None, display: str | None = None) -> dict[str, Any]:
    return {
        "id": key,
        "fullName": full_name or key,
        "displayName": display or key,
        "url": f"/job/{(full_name or key).replace('/', '/job/')}/",
        "buildable": True,
        "labels": ["linux"],
        "state": "ACTIVE",
    }


def build(key: str, owner: str, result: str = "SUCCESS", **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": key,
        "jobKey": owner,
        "number": int(key.rsplit("#", 1)[-1]),
        "displayName": f"#{key.rsplit('#', 1)[-1]}",
        "startedMillis": BASE_TIME - 1000,
        "durationMillis": 500,
        "result": result,
        "state": "RUNNING" if result == "RUNNING" else "ACTIVE",
        "artifacts": [],
    }
    row.update(overrides)
    return row


def node(
    key: str,
    labels: list[str],
    *,
    mode: str = "NORMAL",
    executors: int = 1,
    busy: int = 0,
    online: bool = True,
    accepting: bool = True,
) -> dict[str, Any]:
    return {
        "id": key,
        "name": key,
        "labels": labels,
        "mode": mode,
        "executors": executors,
        "busyExecutors": busy,
        "online": online,
        "acceptingTasks": accepting,
    }


def queued(key: int, owner: str, labels: list[str], *, cancelled: bool = False) -> dict[str, Any]:
    return {
        "id": key,
        "taskKey": owner,
        "labels": labels,
        "enqueuedMillis": BASE_TIME - 10_000,
        "cancelled": cancelled,
        "blockageReason": "cancelled" if cancelled else "",
    }


def fingerprint(
    key: str,
    producer: str,
    consumers: list[str],
    *,
    producer_missing: bool = False,
) -> dict[str, Any]:
    return {
        "id": key,
        "hash": key,
        "producerBuildKey": producer,
        "consumerBuildKeys": consumers,
        "producerMissing": producer_missing,
    }


def plugin(key: str, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": key,
        "shortName": key,
        "displayName": key,
        "version": "1.0",
        "enabled": True,
        "active": True,
        "bundled": False,
        "compatible": True,
        "restartPending": False,
        "missingDependencies": [],
    }
    row.update(overrides)
    return row


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path, *, exclude_target: bool = False) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if exclude_target and (relative == "target" or relative.startswith("target/")):
            continue
        result[relative] = file_digest(path)
    return result


FORBIDDEN_EXPORT_PATTERNS = (
    re.compile(r"https?://", re.I),
    re.compile(r"(password|apikey|api_key|secret_token|private_key)\s*[:=]", re.I),
    re.compile(r"BEGIN (RSA |OPENSSH )?PRIVATE KEY", re.I),
)


def assert_exports_sanitized(home: Path) -> None:
    """Generated exports must not contain credentials, tokens, logs, or external URLs."""
    exports = home / "exports"
    assert exports.is_dir(), "exports directory is required"
    for path in exports.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".log":
            pytest.fail(f"build log artifact present in exports: {path}")
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_EXPORT_PATTERNS:
            assert not pattern.search(text), f"forbidden export content in {path}"
    config = home / "config.json"
    if config.is_file():
        assert json.loads(config.read_text(encoding="utf-8")).get("secrets") is False


def generations(state: Path) -> list[Path]:
    return sorted(path for path in (state / "generations").glob("gen-*") if path.is_dir())


def current_generation(state: Path) -> Path:
    generation_id = (state / "CURRENT").read_text(encoding="utf-8").strip()
    return state / "generations" / generation_id


def records_by_key(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["identity"]["key"]): item for item in result["items"]}


def strip_observation(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = json.loads(json.dumps(items))
    for item in cleaned:
        item.pop("sequence", None)
    return cleaned


def view_payload(result: dict[str, Any]) -> dict[str, Any]:
    assert len(result["items"]) == 1
    return result["items"][0]


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def run_cli_env(
    command: str,
    *options: str,
    home: Path,
    state: Path,
    check: bool = True,
    timeout: int = 120,
) -> dict[str, Any] | subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "JENKINS_HOME": str(home),
        "INSIGHTS_STATE": str(state),
    }
    completed = run_process(
        ["sh", str(INSIGHTS), command, *options],
        check=check,
        env=env,
        timeout=timeout,
    )
    if not check:
        return completed
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        pytest.fail(f"CLI did not emit one JSON object: {completed.stdout!r}: {error}")


def fetch_json(url: str, timeout: float = 1.0) -> tuple[int, dict[str, Any]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as reply:
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


@pytest.fixture(scope="session", autouse=True)
def compiled_core() -> None:
    """Compile the submitted dependency-free Java core once for all tests."""
    assert BUILD_CORE.is_file(), "/app/plugin/bin/build-core is required"
    assert INSIGHTS.is_file(), "/app/plugin/bin/insights is required"
    run_process(["sh", str(BUILD_CORE)], timeout=300)
    assert (PLUGIN / "target/core-classes/io/jenkins/plugins/insights/operator/InsightsMain.class").is_file()


@pytest.fixture(scope="session")
def volume_home(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, Any]]:
    """Generate the one high-volume home shared by volume-sensitive checks."""
    home = tmp_path_factory.mktemp("volume-home")
    generated = generate(home, records=10_000)
    return home, generated["summary"]


def test_f2p_build_core_and_full_scan_publish_all_families(
    volume_home: tuple[Path, dict[str, Any]], tmp_path: Path
) -> None:
    """A bounded full scan publishes all six families and isolates sparse malformed rows."""
    home, inventory = volume_home
    result = run_cli(home, tmp_path / "state", "reconcile", timeout=300)
    assert result["records"] == inventory["total"]
    assert result["manifest"]["recordCount"] == inventory["total"]
    assert result["health"]["sourceErrors"] == inventory["malformed"] == 2
    assert set(result["manifest"]["checksums"]) >= {
        "jobs.json",
        "builds.json",
        "queues.json",
        "nodes.json",
        "fingerprints.json",
        "plugins.json",
    }


def test_f2p_deterministic_10000_home_generation(
    volume_home: tuple[Path, dict[str, Any]], tmp_path: Path
) -> None:
    """The minimum supported high-volume home is byte deterministic for a fixed seed."""
    first_home, first_summary = volume_home
    second_home = tmp_path / "second"
    second_summary = generate(second_home, records=10_000)["summary"]
    assert first_summary == second_summary
    assert tree_digest(first_home) == tree_digest(second_home)
    assert 10_000 <= first_summary["total"] <= 20_000
    assert_exports_sanitized(first_home)


def test_f2p_repeated_full_scans_have_stable_content_digest(
    volume_home: tuple[Path, dict[str, Any]], tmp_path: Path
) -> None:
    """Repeated scans of unchanged source state publish distinct, equivalent generations."""
    home, _ = volume_home
    state = tmp_path / "state"
    first = run_cli(home, state, "reconcile", timeout=300)
    second = run_cli(home, state, "reconcile", timeout=300)
    assert first["generationId"] != second["generationId"]
    assert first["manifest"]["contentDigest"] == second["manifest"]["contentDigest"]
    assert len(generations(state)) >= 2


def test_f2p_full_and_incremental_paths_converge(tmp_path: Path) -> None:
    """An upsert event and a subsequent full scan converge on equivalent canonical records."""
    home = make_home(tmp_path / "home", jobs=[job("job-a")])
    event_state = tmp_path / "event-state"
    run_cli(home, event_state, "reconcile")
    updated = job("job-a", display="Renamed")
    write_rows(home / "exports/jobs.ndjson", [updated])
    run_cli(
        home,
        event_state,
        "event",
        "--source",
        "job",
        "--key",
        "job-a",
        "--event-id",
        "rename-1",
        "--display",
        "Renamed",
        "--field",
        "fullName=job-a",
        "--field",
        "url=/job/job-a/",
    )
    incremental = query(home, event_state, "--kind", "job", "--limit", "100")
    full_state = tmp_path / "full-state"
    run_cli(home, full_state, "reconcile")
    rescanned = query(home, full_state, "--kind", "job", "--limit", "100")
    assert strip_observation(incremental["items"]) == strip_observation(rescanned["items"])


def test_f2p_nested_identity_and_rename_are_stable(tmp_path: Path) -> None:
    """Repeated leaf names remain distinct and renames preserve authority-backed identity."""
    home = make_home(
        tmp_path / "home",
        jobs=[job("authority-a", "team-a/build", "Build"), job("authority-b", "team-b/build", "Build")],
    )
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    before = records_by_key(query(home, state, "--kind", "job"))
    assert set(before) == {"authority-a", "authority-b"}
    write_rows(
        home / "exports/jobs.ndjson",
        [job("authority-a", "renamed/build", "New Name"), job("authority-b", "team-b/build", "Build")],
    )
    run_cli(home, state, "reconcile")
    after = records_by_key(query(home, state, "--kind", "job"))
    assert set(after) == set(before)
    assert after["authority-a"]["fullName"] == "renamed/build"


def test_f2p_malformed_rows_are_isolated_per_record(tmp_path: Path) -> None:
    """Malformed rows become errors without hiding valid rows before or after them."""
    home = make_home(
        tmp_path / "home",
        jobs=[job("job-a")],
        builds=[build("job-a#1", "job-a"), '{"id":"bad","number":', build("job-a#2", "job-a")],
        nodes=[node("good-a", ["linux"]), {"id": "bad-node", "name": "bad", "executors": -1}, node("good-b", ["linux"])],
    )
    state = tmp_path / "state"
    reconciled = run_cli(home, state, "reconcile")
    builds = query(home, state, "--kind", "build")
    nodes = query(home, state, "--kind", "node")
    assert {item["identity"]["key"] for item in builds["items"]} == {"job-a#1", "job-a#2"}
    assert {item["identity"]["key"] for item in nodes["items"]} == {"good-a", "good-b"}
    assert reconciled["health"]["sourceErrors"] == 2


def test_f2p_fingerprint_capability_distinguishes_unsupported_from_empty(tmp_path: Path) -> None:
    """Unsupported fingerprint enumeration is not reported as a supported empty inventory."""
    unsupported_home = make_home(tmp_path / "unsupported", fingerprint_enumeration=False)
    unsupported = run_cli(unsupported_home, tmp_path / "unsupported-state", "reconcile")
    empty_home = make_home(tmp_path / "empty", fingerprint_enumeration=True)
    empty = run_cli(empty_home, tmp_path / "empty-state", "reconcile")
    assert "FINGERPRINT" in unsupported["health"]["unsupportedSources"]
    assert "FINGERPRINT" not in empty["health"]["unsupportedSources"]


def test_f2p_event_exact_retry_is_idempotent_and_conflict_rejected(tmp_path: Path) -> None:
    """Exact event retries are no-ops while identity reuse with another payload is rejected."""
    home = make_home(tmp_path / "home")
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    options = (
        "--source",
        "job",
        "--key",
        "event-job",
        "--event-id",
        "event-42",
        "--display",
        "Original",
        "--field",
        "fullName=event-job",
    )
    first = run_cli(home, state, "event", *options)
    journal_after_first = (state / "journal/events.ndjson").read_bytes()
    retry = run_cli(home, state, "event", *options)
    assert first["applied"] == 1
    assert retry["applied"] == 0
    assert (state / "journal/events.ndjson").read_bytes() == journal_after_first
    conflict = run_cli(home, state, "event", *options[:-3], "Changed", "--field", "fullName=event-job", check=False)
    assert conflict.returncode != 0
    assert b"Original" in json.dumps(records_by_key(query(home, state, "--kind", "job"))).encode()


def test_f2p_delete_fences_stale_retried_upsert(tmp_path: Path) -> None:
    """A duplicate old upsert cannot resurrect a record after a newer delete."""
    home = make_home(tmp_path / "home")
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    upsert = ("--source", "job", "--key", "fenced", "--event-id", "old-upsert", "--field", "fullName=fenced")
    run_cli(home, state, "event", *upsert)
    run_cli(
        home,
        state,
        "event",
        "--source",
        "job",
        "--operation",
        "delete",
        "--key",
        "fenced",
        "--event-id",
        "new-delete",
    )
    run_cli(home, state, "event", *upsert)
    visible = records_by_key(query(home, state, "--kind", "job"))
    assert "fenced" not in visible or visible["fenced"]["state"] == "DELETED"


def test_f2p_checkpoint_restart_replays_unpublished_tail_once(tmp_path: Path) -> None:
    """Restart replays journal entries after the selected checkpoint without duplication and isolates torn tails."""
    home = make_home(tmp_path / "home")
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    base = current_generation(state)
    run_cli(
        home,
        state,
        "event",
        "--source",
        "job",
        "--key",
        "replayed",
        "--event-id",
        "tail-1",
        "--field",
        "fullName=replayed",
    )
    latest = current_generation(state)
    assert latest != base
    shutil.rmtree(latest)
    (state / "CURRENT").write_text(base.name + "\n", encoding="utf-8")
    restarted = run_cli(home, state, "restart")
    assert restarted["records"] == 1
    health = restarted["health"]
    assert health["checkpoint"] == health["journalTail"] == 1
    again = run_cli(home, state, "restart")
    assert again["records"] == 1

    torn_home = make_home(tmp_path / "torn-home")
    torn_state = tmp_path / "torn-state"
    run_cli(torn_home, torn_state, "reconcile")
    run_cli(
        torn_home,
        torn_state,
        "event",
        "--source",
        "job",
        "--key",
        "prefix-job",
        "--event-id",
        "prefix-1",
        "--field",
        "fullName=prefix-job",
    )
    journal = torn_state / "journal" / "events.ndjson"
    with journal.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write('{"sequence":99,"eventId":"torn-2","source":"JOB","operation":"UPSERT","broken":true\n')
    torn_restart = run_cli(torn_home, torn_state, "restart")
    torn_keys = {item["identity"]["key"] for item in query(torn_home, torn_state)["items"]}
    assert "prefix-job" in torn_keys
    assert "torn-job" not in torn_keys
    assert torn_restart["health"]["ready"] is True


def test_f2p_queue_label_conjunction_and_exclusive_mode(tmp_path: Path) -> None:
    """Queue matching honors conjunctive labels and exclusive-node unlabeled rejection."""
    home = make_home(
        tmp_path / "home",
        jobs=[job("job-a")],
        queue=[queued(1, "job-a", ["linux", "docker"]), queued(2, "job-a", []), queued(3, "job-a", ["gpu"])],
        nodes=[node("partial", ["linux"], mode="EXCLUSIVE"), node("exclusive", ["gpu"], mode="EXCLUSIVE")],
    )
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    items = {item["queueKey"]: item for item in view_payload(query(home, state, "--view", "queue"))["items"]}
    assert items["1"]["blockage"] == "LABEL_MISMATCH"
    assert items["2"]["blockage"] == "EXCLUSIVE_REJECTED"
    assert items["3"]["blockage"] == "RUNNABLE"


def test_f2p_queue_offline_no_executor_and_cancelled_semantics(tmp_path: Path) -> None:
    """Offline, exhausted, and cancelled queue items have distinct classes and demand semantics."""
    home = make_home(
        tmp_path / "home",
        jobs=[job("job-a")],
        queue=[queued(1, "job-a", ["offline"]), queued(2, "job-a", ["busy"]), queued(3, "job-a", ["busy"], cancelled=True)],
        nodes=[node("off", ["offline"], online=False), node("busy", ["busy"], executors=2, busy=2)],
    )
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    summary = view_payload(query(home, state, "--view", "queue"))
    classes = {item["queueKey"]: item["blockage"] for item in summary["items"]}
    assert classes == {"1": "OFFLINE", "2": "NO_EXECUTOR", "3": "CANCELLED"}
    assert summary["demand"] == 2


def test_f2p_queue_pressure_handles_empty_and_zero_capacity_demand(tmp_path: Path) -> None:
    """Pressure is zero for no demand and unbounded for demand with zero usable capacity."""
    empty_home = make_home(tmp_path / "empty")
    empty_state = tmp_path / "empty-state"
    run_cli(empty_home, empty_state, "reconcile")
    assert view_payload(query(empty_home, empty_state, "--view", "queue"))["pressure"] == 0
    demand_home = make_home(tmp_path / "demand", jobs=[job("job-a")], queue=[queued(1, "job-a", ["linux"])])
    demand_state = tmp_path / "demand-state"
    run_cli(demand_home, demand_state, "reconcile")
    pressure = view_payload(query(demand_home, demand_state, "--view", "queue"))["pressure"]
    assert pressure == "unbounded"


def test_f2p_build_running_missing_and_malformed_semantics(tmp_path: Path) -> None:
    """Build health separates running, missing, and malformed records from completed outcomes."""
    home = make_home(
        tmp_path / "home",
        jobs=[job("job-a")],
        builds=[
            build("job-a#1", "job-a", "SUCCESS"),
            build("job-a#2", "job-a", "RUNNING", durationMillis=0),
            build("job-a#3", "job-a", "MISSING", durationMillis=0),
            build("job-a#4", "job-a", "MALFORMED", durationMillis=0, state="MALFORMED"),
        ],
    )
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    health = view_payload(query(home, state, "--view", "builds"))["jobs"][0]
    assert (health["total"], health["success"], health["running"], health["missing"], health["malformed"]) == (4, 1, 1, 1, 1)
    assert health["successRate"] == 1.0


def test_f2p_lineage_missing_endpoints_deduplicates_and_reports_cycles(tmp_path: Path) -> None:
    """Lineage preserves missing endpoints, deduplicates consumers, and diagnoses cycles."""
    home = make_home(
        tmp_path / "home",
        jobs=[job("job-a"), job("job-b")],
        builds=[build("job-a#1", "job-a"), build("job-b#1", "job-b")],
        fingerprints=[
            fingerprint("fp-a", "job-a#1", ["job-b#1", "job-b#1", "missing#1"]),
            fingerprint("fp-b", "job-b#1", ["job-a#1"]),
            fingerprint("fp-missing", "gone#1", ["job-a#1"], producer_missing=True),
        ],
    )
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    lineage = view_payload(query(home, state, "--view", "lineage"))
    assert len(lineage["edges"]) == 4
    assert lineage["missingProducers"] == 1
    assert lineage["missingConsumers"] == 1
    assert lineage["cycles"]


def test_f2p_referenced_deleted_endpoints_remain_as_tombstones(tmp_path: Path) -> None:
    """A retained fingerprint keeps deleted build lineage resolvable through a tombstone."""
    home = make_home(
        tmp_path / "home",
        jobs=[job("producer"), job("consumer")],
        builds=[build("producer#1", "producer"), build("consumer#1", "consumer")],
        fingerprints=[fingerprint("fp", "producer#1", ["consumer#1"])],
    )
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    run_cli(
        home,
        state,
        "event",
        "--source",
        "build",
        "--operation",
        "delete",
        "--key",
        "producer#1",
        "--event-id",
        "delete-producer",
    )
    build_records = records_by_key(query(home, state, "--kind", "build"))
    assert build_records["producer#1"]["state"] == "DELETED"
    edge = view_payload(query(home, state, "--view", "lineage"))["edges"][0]
    assert edge["producerBuildKey"] == "producer#1"


def test_f2p_offline_plugin_inventory_classifies_all_states(tmp_path: Path) -> None:
    """Installed metadata alone classifies plugin lifecycle, compatibility, dependency, and restart state."""
    home = make_home(
        tmp_path / "home",
        plugins=[
            plugin("enabled"),
            plugin("disabled", enabled=False, active=False),
            plugin("failed", active=False),
            plugin("bundled", bundled=True),
            plugin("incompatible", compatible=False),
            plugin("dependency", missingDependencies=["missing-api"]),
            plugin("restart", restartPending=True),
        ],
    )
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    summary = view_payload(query(home, state, "--view", "plugins"))
    by_name = {item["shortName"]: item for item in summary["plugins"]}
    assert by_name["enabled"]["state"] == "ENABLED"
    assert by_name["disabled"]["state"] == "DISABLED"
    assert by_name["failed"]["state"] == "FAILED"
    assert by_name["bundled"]["bundled"] is True
    assert by_name["incompatible"]["state"] == "INCOMPATIBLE"
    assert by_name["dependency"]["state"] == "DEPENDENCY_MISSING"
    assert by_name["restart"]["state"] == "RESTART_PENDING"
    assert summary["restartRequired"] is True
    assert summary["dependencyFailures"] == 1


def test_f2p_publication_verifies_files_before_current(tmp_path: Path) -> None:
    """Every published CURRENT target is complete and checksum-valid with no staging residue."""
    home = make_home(tmp_path / "home", jobs=[job("job-a")])
    state = tmp_path / "state"
    for index in range(3):
        write_rows(home / "exports/jobs.ndjson", [job("job-a", display=f"name-{index}")])
        run_cli(home, state, "reconcile")
        current = current_generation(state)
        manifest = json.loads((current / "manifest.json").read_text(encoding="utf-8"))
        assert current.name == manifest["generationId"]
        for filename, expected in manifest["checksums"].items():
            assert file_digest(current / filename) == expected
        assert not list((state / "generations").glob(".*.staging"))


def test_f2p_corrupt_newest_generation_falls_back_to_verified_state(tmp_path: Path) -> None:
    """Recovery rejects a corrupt newest generation and deterministically selects a valid fallback."""
    home = make_home(tmp_path / "home", jobs=[job("job-a")])
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    fallback = current_generation(state)
    write_rows(home / "exports/jobs.ndjson", [job("job-a"), job("job-b")])
    run_cli(home, state, "reconcile")
    corrupt = current_generation(state)
    assert corrupt != fallback
    (corrupt / "jobs.json").write_text("[]\n", encoding="utf-8")
    restarted = run_cli(home, state, "restart")
    assert restarted["health"]["ready"] is True
    assert (state / "CURRENT").read_text(encoding="utf-8").strip() == fallback.name
    assert restarted["records"] == 1


def test_f2p_legacy_generation_migrates_without_mutating_source(tmp_path: Path) -> None:
    """Startup migrates legacy state by publishing a new generation and leaves the old generation immutable."""
    home = make_home(tmp_path / "home", jobs=[job("job-a")])
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    legacy = current_generation(state)
    manifest_path = legacy / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schemaVersion"] = 1
    manifest_path.write_text(json.dumps(manifest, separators=(",", ":")) + "\n", encoding="utf-8")
    legacy_digest = tree_digest(legacy)
    run_cli(home, state, "restart")
    migrated = current_generation(state)
    assert migrated != legacy
    assert json.loads((migrated / "manifest.json").read_text(encoding="utf-8"))["schemaVersion"] == 2
    assert tree_digest(legacy) == legacy_digest


def test_f2p_compaction_preserves_current_fallback_and_leases(tmp_path: Path) -> None:
    """Retention keeps CURRENT, a recovery fallback, and leased generations even at retain one."""
    home = make_home(tmp_path / "home", jobs=[job("job-a")])
    state = tmp_path / "state"
    published: list[str] = []
    for index in range(4):
        write_rows(home / "exports/jobs.ndjson", [job("job-a", display=f"v{index}")])
        published.append(run_cli(home, state, "reconcile")["generationId"])
    lease = state / "leases" / f"{published[0]}--reader.lease"
    lease.write_text(published[0] + "\n", encoding="utf-8")
    compacted = run_cli(home, state, "compact", "--retain", "1")
    remaining = {path.name for path in generations(state)}
    assert {published[0], published[-2], published[-1]} <= remaining
    assert published[0] in compacted["leased"]


def test_f2p_shutdown_fences_publication_and_restart_is_ready(tmp_path: Path) -> None:
    """Terminating the long-running HTTP adapter leaves no partial publication and restart remains ready."""
    home = make_home(tmp_path / "home", jobs=[job("job-a")])
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    port = free_port()
    server = subprocess.Popen(
        ["sh", str(INSIGHTS), "serve", "--home", str(home), "--state", str(state), "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                status, payload = fetch_json(f"http://127.0.0.1:{port}/operational-insights/api/v1/health")
                if status == 200 and payload.get("ready"):
                    break
            except (OSError, urllib.error.URLError):
                if time.monotonic() >= deadline:
                    pytest.fail("HTTP service did not become ready")
                time.sleep(0.05)
        server.terminate()
        server.wait(timeout=10)
    finally:
        if server.poll() is None:
            server.kill()
            server.wait(timeout=5)
    assert not list((state / "generations").glob(".*.staging"))
    assert run_cli(home, state, "restart")["health"]["ready"] is True


def test_f2p_acl_projection_precedes_rows_totals_and_facets(tmp_path: Path) -> None:
    """Hidden item records affect neither visible rows, totals, nor family facets."""
    home = make_home(
        tmp_path / "home",
        jobs=[job("visible"), job("hidden")],
        builds=[build("visible#1", "visible"), build("hidden#1", "hidden")],
    )
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    visible = query(home, state, "--item", "visible", "--limit", "100")
    assert {item["identity"]["key"] for item in visible["items"]} == {"visible", "visible#1"}
    assert visible["total"] == 2
    assert visible["facets"] == {"build": 1, "job": 1}
    denied = run_cli(home, state, "query", "--system-read", "false", check=False)
    assert denied.returncode != 0
    assert "generationId" not in denied.stderr and "total" not in denied.stderr


def test_f2p_acl_projection_precedes_lineage_and_summary_aggregation(tmp_path: Path) -> None:
    """Partially hidden lineage and aggregate counts reveal no endpoint or multiplicity."""
    home = make_home(
        tmp_path / "home",
        jobs=[job("visible"), job("hidden")],
        builds=[build("visible#1", "visible"), build("hidden#1", "hidden")],
        fingerprints=[fingerprint("secret-edge", "hidden#1", ["visible#1"])],
    )
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    lineage = view_payload(query(home, state, "--view", "lineage", "--item", "visible"))
    summary = view_payload(query(home, state, "--view", "summary", "--item", "visible"))
    assert lineage["edges"] == []
    assert lineage["fingerprints"] == 0
    assert summary["lineageEdges"] == 0
    assert summary["records"] == 2


def test_f2p_acl_projection_precedes_cursor_pagination(tmp_path: Path) -> None:
    """Hidden records do not consume pages or shift cursors in the authorized result set."""
    home = make_home(tmp_path / "home", jobs=[job("a-hidden"), job("b-visible"), job("c-visible")])
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    first = query(home, state, "--item", "b-visible", "--item", "c-visible", "--limit", "1")
    assert [item["identity"]["key"] for item in first["items"]] == ["b-visible"]
    assert first["total"] == 2 and first["nextCursor"]
    second = query(
        home,
        state,
        "--item",
        "b-visible",
        "--item",
        "c-visible",
        "--limit",
        "1",
        "--cursor",
        first["nextCursor"],
    )
    assert [item["identity"]["key"] for item in second["items"]] == ["c-visible"]
    assert second["nextCursor"] is None


def test_f2p_stable_sorting_cursors_and_filter_errors(tmp_path: Path) -> None:
    """Sort order is stable across pages, contains narrows records, metadata is present, and bad filters fail."""
    home = make_home(tmp_path / "home", jobs=[job("charlie"), job("alpha"), job("bravo")])
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    first = query(home, state, "--sort", "key", "--direction", "desc", "--limit", "2")
    second = query(home, state, "--sort", "key", "--direction", "desc", "--limit", "2", "--cursor", first["nextCursor"])
    assert [item["identity"]["key"] for item in first["items"] + second["items"]] == ["charlie", "bravo", "alpha"]
    contains = query(home, state, "--kind", "job", "--contains", "char")
    assert contains["total"] == 1 and contains["items"][0]["identity"]["key"] == "charlie"
    metadata = query(home, state, "--kind", "job", "--sort", "display", "--direction", "asc", "--limit", "2")["metadata"]
    assert metadata["principal"] == "operator"
    assert metadata["sort"] == "display" and metadata["direction"] == "ASC"
    assert "visible" in metadata and "checkpoint" in metadata
    for invalid in (("--cursor", "not-a-cursor"), ("--sort", "unknown"), ("--limit", "1001")):
        rejected = run_cli(home, state, "query", *invalid, check=False)
        assert rejected.returncode != 0


def test_f2p_cli_and_http_use_equivalent_shared_query_semantics(tmp_path: Path) -> None:
    """CLI and authenticated HTTP return the same query envelope; unauthorized HTTP exposes no result metadata."""
    home = make_home(tmp_path / "home", jobs=[job("alpha"), job("bravo")])
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    expected = query(home, state, "--kind", "job", "--sort", "display", "--direction", "desc", "--limit", "1")
    port = free_port()
    server = subprocess.Popen(
        ["sh", str(INSIGHTS), "serve", "--home", str(home), "--state", str(state), "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    params = urllib.parse.urlencode({"kind": "job", "sort": "display", "direction": "desc", "limit": "1"})
    url = f"http://127.0.0.1:{port}/operational-insights/api/v1/query?{params}"
    denied_url = f"http://127.0.0.1:{port}/operational-insights/api/v1/query?{params}&system-read=false"
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                status, actual = fetch_json(url)
                break
            except (OSError, urllib.error.URLError):
                if time.monotonic() >= deadline:
                    pytest.fail("HTTP query endpoint did not start")
                time.sleep(0.05)
        assert status == 200
        assert response(actual) == expected
        denied_status, denied_payload = fetch_json(denied_url)
        assert denied_status == 403
        assert denied_payload.get("error") == "forbidden"
        assert "generationId" not in denied_payload and "metadata" not in denied_payload and "total" not in denied_payload
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


def test_f2p_readiness_and_supported_empty_home(tmp_path: Path) -> None:
    """A verified empty home is ready, returns a stable empty response, and honors JENKINS_HOME/INSIGHTS_STATE."""
    home = make_home(tmp_path / "home")
    state = tmp_path / "state"
    reconciled = run_cli(home, state, "reconcile")
    health = run_cli(home, state, "health")["health"]
    empty = query(home, state)
    assert reconciled["records"] == 0
    assert health["ready"] is True and health["currentValid"] is True
    assert health["replayLag"] == 0 and health["unsupportedSources"] == []
    assert empty["items"] == [] and empty["total"] == 0 and empty["nextCursor"] is None
    env_home = make_home(tmp_path / "env-home", jobs=[job("env-job")])
    env_state = tmp_path / "env-state"
    env_reconciled = response(run_cli_env("reconcile", home=env_home, state=env_state))
    env_query = response(run_cli_env("query", "--kind", "job", home=env_home, state=env_state))
    assert env_reconciled["records"] == 1
    assert {item["identity"]["key"] for item in env_query["items"]} == {"env-job"}


def test_f2p_repeated_queries_are_byte_deterministic(tmp_path: Path) -> None:
    """Unchanged state produces byte-identical query JSON across independent CLI invocations."""
    home = make_home(tmp_path / "home", jobs=[job("zulu"), job("alpha")])
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    arguments = ["sh", str(INSIGHTS), "query", "--home", str(home), "--state", str(state), "--sort", "key"]
    first = run_process(arguments).stdout
    second = run_process(arguments).stdout
    assert first == second


def test_f2p_jenkins_bindings_expose_required_lifecycle_and_adapters() -> None:
    """The HPI binding declares the required Jenkins lifecycle, listeners, CLI, and RootAction signatures."""
    source = (PLUGIN / "src/main/java/io/jenkins/plugins/insights/jenkins/OperationalInsightsPlugin.java").read_text(encoding="utf-8")
    required_signatures = (
        "@Initializer",
        "@Terminator",
        "extends AsyncPeriodicWork",
        "extends ItemListener",
        "extends RunListener",
        "extends QueueListener",
        "extends ComputerListener",
        "extends CLICommand",
        "implements hudson.model.RootAction",
        "checkPermission(Jenkins.SYSTEM_READ)",
    )
    assert all(signature in source for signature in required_signatures)


def test_p2p_commands_leave_jenkins_owned_home_read_only(tmp_path: Path) -> None:
    """Reconcile, query, event, restart, and compaction never mutate source home files."""
    home = make_home(tmp_path / "home", jobs=[job("job-a")], builds=[build("job-a#1", "job-a")])
    before = tree_digest(home)
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    query(home, state)
    run_cli(home, state, "event", "--source", "job", "--key", "other", "--event-id", "readonly", "--field", "fullName=other")
    run_cli(home, state, "restart")
    run_cli(home, state, "compact", "--retain", "2")
    assert tree_digest(home) == before


def test_p2p_invalid_commands_are_rejected_without_generation_damage(tmp_path: Path) -> None:
    """Invalid commands and requests fail nonzero without changing published generations."""
    home = make_home(tmp_path / "home", jobs=[job("job-a")])
    state = tmp_path / "state"
    run_cli(home, state, "reconcile")
    before = tree_digest(state / "generations")
    assert run_cli(home, state, "destroy", check=False).returncode != 0
    assert run_cli(home, state, "query", "--limit", "0", check=False).returncode != 0
    assert tree_digest(state / "generations") == before


def test_p2p_runtime_has_no_network_requirement(tmp_path: Path) -> None:
    """Core build outputs operate with unreachable proxy settings and no external service."""
    home = make_home(tmp_path / "home", jobs=[job("offline")], plugins=[plugin("installed")])
    state = tmp_path / "state"
    env = os.environ.copy()
    env.update(
        {
            "http_proxy": "http://127.0.0.1:9",
            "https_proxy": "http://127.0.0.1:9",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "",
        }
    )
    reconciled = run_cli(home, state, "reconcile", env=env)
    assert reconciled["records"] == 2
    queried = response(run_cli(home, state, "query", "--view", "plugins", env=env))
    assert queried["total"] >= 1


def test_p2p_task_package_preserves_solver_visible_shape() -> None:
    """The delivered artifact retains the documented source, scripts, configuration, and HPI metadata."""
    required = (
        "README.md",
        "pom.xml",
        "bin/build-core",
        "bin/insights",
        "config/insights.properties",
        "docs/api-v1.md",
        "docs/authorization.md",
        "docs/generated-home.md",
        "docs/operations.md",
        "docs/storage.md",
        "src/main/java/io/jenkins/plugins/insights/operator/InsightsMain.java",
        "src/main/java/io/jenkins/plugins/insights/jenkins/OperationalInsightsPlugin.java",
    )
    assert all((PLUGIN / relative).is_file() for relative in required)