from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path("/app/continuity")
sys.path.insert(0, str(ROOT))

from continuity.engine import ContinuityEngine  # noqa: E402
from continuity.model import FencingError, GenerationStatus  # noqa: E402
from continuity.store import ContinuityStore  # noqa: E402


def _build_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript((ROOT / "sql/schema.sql").read_text(encoding="utf-8"))
        connection.executescript(
            (ROOT / "sql/runtime_extensions.sql").read_text(encoding="utf-8")
        )
        connection.executescript((ROOT / "sql/seed.sql").read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()


@pytest.fixture(scope="session")
def contract_baseline_database(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("continuity-contract-baseline") / "continuity.db"
    _build_database(path)
    return path


@pytest.fixture
def contract_engine(
    tmp_path: Path, contract_baseline_database: Path
) -> ContinuityEngine:
    database = tmp_path / "continuity.db"
    shutil.copy2(contract_baseline_database, database)
    store = ContinuityStore(database)
    return ContinuityEngine.from_json_file(store, ROOT / "config/continuity.json")


def _complete_archive(engine: ContinuityEngine, region: str) -> None:
    base = 100_000 if region == "east" else 200_000
    stream = "EDGE_EAST_TELEMETRY" if region == "east" else "EDGE_WEST_TELEMETRY"
    domain = "edge-east" if region == "east" else "edge-west"
    engine.store.execute(
        "INSERT INTO archive_index(event_id,region,generation,origin_sequence,hub_stream_sequence,payload_sha256,archived_at,source_stream,source_domain,duplicate_observation_count) "
        "SELECT j.event_id,j.region,j.generation,j.origin_sequence,?+j.origin_sequence,j.payload_sha256,"
        "datetime(j.accepted_at,'+4 seconds'),?,?,0 FROM event_journal j "
        "WHERE j.region=? AND NOT EXISTS(SELECT 1 FROM archive_index a WHERE a.event_id=j.event_id)",
        (base, stream, domain, region),
    )
    engine.store.execute(
        "UPDATE event_journal SET publish_state='ARCHIVED',archive_confirmed_at=COALESCE(archive_confirmed_at,datetime(accepted_at,'+4 seconds')) WHERE region=?",
        (region,),
    )


def _set_required_consumers(
    engine: ContinuityEngine, region: str, sequence: int
) -> None:
    for consumer in engine.store.required_consumers():
        event_id = f"evt-{region}-g01-{sequence:06d}"
        engine.store.execute(
            "INSERT INTO consumer_checkpoints(consumer_name,region,generation,last_effect_sequence,last_ack_sequence,last_event_id,jetstream_ack_floor,updated_at) "
            "VALUES(?,?,1,?,?,?,?,?) ON CONFLICT(consumer_name,region,generation) DO UPDATE SET "
            "last_effect_sequence=excluded.last_effect_sequence,last_ack_sequence=excluded.last_ack_sequence,last_event_id=excluded.last_event_id,"
            "jetstream_ack_floor=excluded.jetstream_ack_floor,updated_at=excluded.updated_at",
            (
                consumer,
                region,
                sequence,
                sequence,
                event_id,
                sequence,
                "2026-08-09T00:00:00Z",
            ),
        )


def _operator_root(tmp_path: Path) -> Path:
    root = tmp_path / "operator-runtime"
    (root / "state").mkdir(parents=True)
    (root / "config").mkdir(parents=True)
    (root / "out").mkdir(parents=True)
    shutil.copy2(ROOT / "state/continuity.db", root / "state/continuity.db")
    shutil.copy2(ROOT / "config/continuity.json", root / "config/continuity.json")
    return root


def _protected_state_digest(database: Path) -> str:
    tables = (
        "event_journal",
        "archive_index",
        "origin_generations",
        "processing_effects",
        "consumer_checkpoints",
        "replay_plans",
        "replay_plan_items",
        "recovery_leases",
        "retention_watermarks",
    )
    connection = sqlite3.connect(database)
    try:
        digest = hashlib.sha256()
        for table in tables:
            rows = connection.execute(
                f'SELECT * FROM "{table}" ORDER BY rowid'
            ).fetchall()
            digest.update(table.encode("utf-8"))
            digest.update(
                json.dumps(rows, separators=(",", ":"), default=str).encode("utf-8")
            )
        return digest.hexdigest()
    finally:
        connection.close()


# ---- F2P: solver-visible contract gaps ---------------------------------------------------


def test_f2p_expired_lease_reacquired_by_same_owner_advances_epoch(
    contract_engine: ContinuityEngine,
) -> None:
    """A restarted worker cannot reuse its old fence merely because its owner id is unchanged."""
    t0 = datetime(2026, 8, 9, 3, 30, tzinfo=UTC)
    first = contract_engine.acquire_recovery_lease(
        region="east",
        owner_id="regional-recovery-worker",
        ttl_seconds=5,
        at=t0,
    )
    reacquired = contract_engine.acquire_recovery_lease(
        region="east",
        owner_id="regional-recovery-worker",
        ttl_seconds=30,
        at=t0 + timedelta(seconds=6),
    )

    assert reacquired.fence_epoch > first.fence_epoch
    with pytest.raises(FencingError):
        contract_engine.assert_recovery_fence(
            region="east",
            owner_id="regional-recovery-worker",
            fence_epoch=first.fence_epoch,
            at=t0 + timedelta(seconds=7),
        )


def test_f2p_final_health_and_reconciliation_reports_are_materialized(
    tmp_path: Path,
) -> None:
    """Final reports match independently recomputed durable state and preserve incident evidence."""
    health_path = ROOT / "out/health.json"
    reconciliation_path = ROOT / "out/reconciliation.json"
    assert health_path.is_file(), (
        "solution must materialize /app/continuity/out/health.json"
    )
    assert reconciliation_path.is_file(), (
        "solution must materialize /app/continuity/out/reconciliation.json"
    )

    health = json.loads(health_path.read_text(encoding="utf-8"))
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))

    expected_database = tmp_path / "expected-report-state.db"
    shutil.copy2(ROOT / "state/continuity.db", expected_database)
    expected_engine = ContinuityEngine.from_json_file(
        ContinuityStore(expected_database),
        ROOT / "config/continuity.json",
    )
    expected_health = expected_engine.inspect_health().as_dict()
    expected_regions = {
        region: summary.as_dict()
        for region, summary in expected_engine.reconcile_all().items()
    }

    for key in (
        "healthy",
        "topology_ok",
        "generations_ok",
        "publication_ok",
        "archive_ok",
        "consumers_ok",
        "retention_ok",
        "recovery_ok",
    ):
        assert health[key] == expected_health[key]

    assert set(reconciliation["regions"]) == {"east", "west"}
    assert reconciliation["converged"] == all(
        summary["converged"] for summary in expected_regions.values()
    )
    fields = (
        "status",
        "journal_event_count",
        "archive_event_count",
        "missing_count",
        "unexpected_count",
        "duplicate_count",
        "metadata_mismatch_count",
        "consumer_lag_count",
        "checksum",
        "findings",
        "converged",
    )
    for region, expected in expected_regions.items():
        actual = reconciliation["regions"][region]
        for field in fields:
            assert actual[field] == expected[field]

    connection = sqlite3.connect(ROOT / "state/continuity.db")
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM event_journal").fetchone()[0]
            == 12000
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM consumer_checkpoints").fetchone()[
                0
            ]
            >= 4
        )
        active_plans = connection.execute(
            "SELECT COUNT(*) FROM replay_plans WHERE status IN ('APPROVED','RUNNING')"
        ).fetchone()[0]
        assert active_plans >= 1
    finally:
        connection.close()

    stream_state = json.loads(
        (ROOT / "ops/stream-state.json").read_text(encoding="utf-8")
    )
    assert stream_state["incident_id"] == "INC-JS-2026-0808-17"
    assert stream_state["captured_at"] == "2026-08-08T17:18:10Z"
    assert stream_state["domains"]["hub"]["messages"] == 11395
    assert stream_state["domains"]["hub"]["sources"][1]["domain"] == "edge-east"
    handoff = (ROOT / "ops/shift-handoff.txt").read_text(encoding="utf-8")
    assert "three west identities and two east identities" in handoff


# ---- P2P: already-correct detailed contract behavior ------------------------------------


def test_p2p_diagnostic_cli_commands_do_not_mutate_recovery_state(
    tmp_path: Path,
) -> None:
    """Inspect, reconcile and verify may record observations but do not mutate recovery state."""
    runtime_root = _operator_root(tmp_path)
    database = runtime_root / "state/continuity.db"
    before = _protected_state_digest(database)

    for command in ("inspect", "reconcile", "verify"):
        completed = subprocess.run(
            [
                str(ROOT / "bin/continuityctl"),
                command,
                "--root",
                str(runtime_root),
                "--compact",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        assert completed.returncode in {0, 2}, completed.stderr
        assert _protected_state_digest(database) == before


def test_p2p_stale_lease_release_is_rejected(contract_engine: ContinuityEngine) -> None:
    """A stale epoch cannot release the currently owned recovery lease."""
    now = datetime.now(UTC)
    current = contract_engine.store.write_lease(
        region="east",
        owner_id="release-worker",
        fence_epoch=7,
        acquired_at=now,
        renewed_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    with pytest.raises(FencingError):
        contract_engine.store.release_lease(
            "east",
            owner_id="release-worker",
            fence_epoch=6,
            at=now + timedelta(seconds=1),
        )
    after = contract_engine.store.current_lease("east")
    assert after is not None and after.fence_epoch == current.fence_epoch


def test_p2p_cleanup_respects_minimum_age_and_explicit_holds(
    contract_engine: ContinuityEngine,
) -> None:
    """Even below the convergence watermark, young rows and explicit holds are never cleanup candidates."""
    _complete_archive(contract_engine, "east")
    _set_required_consumers(contract_engine, "east", 6000)

    contract_engine.store.execute(
        "UPDATE event_journal SET retention_hold=1,accepted_at='2026-08-01T00:00:00Z' "
        "WHERE region='east' AND generation=1 AND origin_sequence=100"
    )
    contract_engine.store.execute(
        "UPDATE event_journal SET retention_hold=0,accepted_at='2026-08-09T04:30:00Z' "
        "WHERE region='east' AND generation=1 AND origin_sequence=101"
    )
    contract_engine.store.execute(
        "UPDATE event_journal SET retention_hold=0,accepted_at='2026-08-01T00:00:00Z' "
        "WHERE region='east' AND generation=1 AND origin_sequence=102"
    )

    decision = contract_engine.compute_retention_decision(
        region="east",
        generation=1,
        at=datetime(2026, 8, 9, 5, 0, tzinfo=UTC),
        limit=500,
    )
    candidates = set(decision.eligible_event_ids)

    assert "evt-east-g01-000100" not in candidates
    assert "evt-east-g01-000101" not in candidates
    assert "evt-east-g01-000102" in candidates


def test_p2p_generation_approval_does_not_rewrite_historical_events(
    contract_engine: ContinuityEngine,
) -> None:
    """Approving a new origin generation leaves previously accepted event identities on their original generation."""
    historical = contract_engine.store.event_by_origin("east", 1, 100)
    assert historical is not None

    pending = contract_engine.store.record_pending_generation(
        "east",
        generation=2,
        stream_fingerprint="east-recreated-contract-check",
        first_sequence=1,
        last_observed_sequence=25,
        at=datetime(2026, 8, 9, 6, 0, tzinfo=UTC),
    )
    assert pending.status is GenerationStatus.PENDING_APPROVAL
    approved = contract_engine.store.approve_generation(
        "east",
        2,
        approved_by="shift-lead",
        at=datetime(2026, 8, 9, 6, 1, tzinfo=UTC),
    )
    assert approved.status is GenerationStatus.CONFIRMED

    after = contract_engine.store.event_by_id(historical.identity.event_id)
    assert after is not None
    assert after.identity.generation == 1
    assert after.identity.origin_sequence == historical.identity.origin_sequence


def test_p2p_recovery_cli_entrypoints_remain_operational(tmp_path: Path) -> None:
    """Existing generation, replay, lease, execute and retention commands remain wired to durable state."""
    runtime_root = _operator_root(tmp_path)
    database = runtime_root / "state/continuity.db"
    engine = ContinuityEngine.from_json_file(
        ContinuityStore(database), runtime_root / "config/continuity.json"
    )
    engine.store.execute("DELETE FROM recovery_leases")

    def run_cli(*args: str, allowed: set[int] = {0}) -> dict[str, object]:
        completed = subprocess.run(
            [str(ROOT / "bin/continuityctl"), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        assert completed.returncode in allowed, completed.stderr
        return json.loads(completed.stdout)

    planned = run_cli(
        "plan-replay",
        "east",
        "--generation",
        "1",
        "--created-by",
        "cli-contract-test",
        "--reason",
        "exercise preserved recovery CLI",
        "--approve",
        "--approved-by",
        "cli-contract-test",
        "--root",
        str(runtime_root),
        "--compact",
    )
    assert planned["blocked_reason"] is None
    assert planned["plan"] is not None

    listed = run_cli(
        "list-replay",
        "--region",
        "east",
        "--root",
        str(runtime_root),
        "--compact",
    )
    assert any(plan["plan_id"] == planned["plan"]["plan_id"] for plan in listed)

    retention = run_cli(
        "retention",
        "east",
        "--generation",
        "1",
        "--limit",
        "5",
        "--root",
        str(runtime_root),
        "--compact",
        allowed={0, 2},
    )
    assert retention["region"] == "east"
    assert "safe_sequence" in retention and "eligible_event_ids" in retention

    _complete_archive(engine, "west")
    acquired = run_cli(
        "lease",
        "--root",
        str(runtime_root),
        "--compact",
        "acquire",
        "west",
        "--owner",
        "cli-recovery-worker",
        "--ttl",
        "300",
    )
    epoch = int(acquired["fence_epoch"])

    executed = run_cli(
        "execute-replay",
        "rp-west-incident-001",
        "--owner",
        "cli-recovery-worker",
        "--epoch",
        str(epoch),
        "--root",
        str(runtime_root),
        "--compact",
    )
    assert executed["completed"] is True
    replay_after = engine.store.replay_plan("rp-west-incident-001")
    assert replay_after is not None and replay_after.status.value == "COMPLETED"

    renewed = run_cli(
        "lease",
        "--root",
        str(runtime_root),
        "--compact",
        "renew",
        "west",
        "--owner",
        "cli-recovery-worker",
        "--epoch",
        str(epoch),
        "--ttl",
        "300",
    )
    assert int(renewed["fence_epoch"]) == epoch
    released = run_cli(
        "lease",
        "--root",
        str(runtime_root),
        "--compact",
        "release",
        "west",
        "--owner",
        "cli-recovery-worker",
        "--epoch",
        str(epoch),
    )
    assert released["released"] is True
    assert engine.store.current_lease("west") is None

    pending = engine.store.record_pending_generation(
        "east",
        generation=2,
        stream_fingerprint="cli-pending-generation-2",
        first_sequence=1,
        last_observed_sequence=10,
        at=datetime(2026, 8, 9, 7, 0, tzinfo=UTC),
    )
    assert pending.status is GenerationStatus.PENDING_APPROVAL
    approved = run_cli(
        "approve-generation",
        "east",
        "2",
        "--approved-by",
        "cli-contract-test",
        "--root",
        str(runtime_root),
        "--compact",
    )
    assert approved["status"] == "CONFIRMED"

    generations = run_cli(
        "generations",
        "--region",
        "east",
        "--root",
        str(runtime_root),
        "--compact",
    )
    assert any(
        row["generation"] == 2 and row["status"] == "CONFIRMED" for row in generations
    )
