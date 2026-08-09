from __future__ import annotations

import asyncio
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
from continuity.runtime import (  # noqa: E402
    JetStreamAdmin,
    LabProcessManager,
    NatsConnectionPool,
    endpoints_from_engine,
)
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
    """Verify emits independently truthful reports and preserves captured incident evidence."""
    runtime_root = _operator_root(tmp_path)
    completed = subprocess.run(
        [
            str(ROOT / "bin/continuityctl"),
            "verify",
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

    health_path = runtime_root / "out/health.json"
    reconciliation_path = runtime_root / "out/reconciliation.json"
    assert health_path.is_file()
    assert reconciliation_path.is_file()
    health = json.loads(health_path.read_text(encoding="utf-8"))
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    config = json.loads(
        (runtime_root / "config/continuity.json").read_text(encoding="utf-8")
    )

    def contiguous_floor(values: list[int]) -> int:
        present = set(values)
        floor = 0
        while floor + 1 in present:
            floor += 1
        return floor

    topology = config["topology"]
    edge_streams = topology["edge_streams"]
    hub_archive = topology["hub_archive"]
    sources = {item["region"]: item for item in topology["sources"]}
    physical_names = [
        hub_archive["name"],
        edge_streams["east"]["name"],
        edge_streams["west"]["name"],
    ]
    expected_topology_ok = (
        len(physical_names) == len(set(physical_names))
        and not hub_archive.get("subjects")
        and all(
            edge_streams[region]["name"]
            == config["regions"][region]["stream_name"]
            and edge_streams[region]["domain"]
            == config["regions"][region]["domain"]
            and sources[region]["origin"]["name"]
            == edge_streams[region]["name"]
            and sources[region]["origin"]["domain"]
            == edge_streams[region]["domain"]
            for region in ("east", "west")
        )
        and str(topology["derived_subject_prefix"]).startswith(
            "telemetry.derived"
        )
        and not str(topology["derived_subject_prefix"]).startswith(
            "telemetry.raw"
        )
    )

    recovery = config["recovery"]
    required_horizon = (
        int(recovery["maximum_disconnect_seconds"])
        + int(recovery["maximum_replay_seconds"])
        + int(recovery["safety_margin_seconds"])
    )
    expected_retention_ok = (
        all(
            int(config["regions"][region]["stream_policy"]["max_age_seconds"])
            >= required_horizon
            for region in ("east", "west")
        )
        and int(config["hub_stream_policy"]["max_age_seconds"])
        >= required_horizon
    )

    connection = sqlite3.connect(runtime_root / "state/continuity.db")
    connection.row_factory = sqlite3.Row
    try:
        required_consumers = [
            str(row["consumer_name"])
            for row in connection.execute(
                "SELECT consumer_name FROM consumer_registry WHERE required=1 AND enabled=1 ORDER BY consumer_name"
            ).fetchall()
        ]
        active_plans = int(
            connection.execute(
                "SELECT COUNT(*) FROM replay_plans WHERE status IN ('APPROVED','RUNNING')"
            ).fetchone()[0]
        )
        expected_recovery_ok = active_plans == 0
        expected_generations_ok = True
        expected_publication_ok = (
            int(
                connection.execute(
                    "SELECT COUNT(*) FROM event_journal WHERE publish_state IN ('PUBLISHING','RETRY','HELD')"
                ).fetchone()[0]
            )
            == 0
        )
        expected_consumers_ok = True
        expected_region_convergence: dict[str, bool] = {}

        assert set(reconciliation["regions"]) == {"east", "west"}
        for region in ("east", "west"):
            confirmed = connection.execute(
                "SELECT generation,last_observed_sequence FROM origin_generations "
                "WHERE region=? AND status='CONFIRMED' ORDER BY generation",
                (region,),
            ).fetchall()
            pending_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM origin_generations WHERE region=? AND status='PENDING_APPROVAL'",
                    (region,),
                ).fetchone()[0]
            )
            if len(confirmed) != 1 or pending_count:
                expected_generations_ok = False
            assert confirmed, f"{region} must retain a confirmed generation"
            generation = int(confirmed[-1]["generation"])
            confirmed_watermark = int(
                confirmed[-1]["last_observed_sequence"]
            )
            region_row = connection.execute(
                "SELECT physical_stream,jetstream_domain FROM regions WHERE region=?",
                (region,),
            ).fetchone()
            assert region_row is not None
            expected_stream = str(region_row["physical_stream"])
            expected_domain = str(region_row["jetstream_domain"])

            journal_rows = connection.execute(
                "SELECT event_id,origin_sequence,payload_sha256 FROM event_journal "
                "WHERE region=? AND generation=?",
                (region, generation),
            ).fetchall()
            archive_rows = connection.execute(
                "SELECT event_id,origin_sequence,payload_sha256,source_stream,source_domain,duplicate_observation_count "
                "FROM archive_index WHERE region=? AND generation=?",
                (region, generation),
            ).fetchall()
            journal = {
                str(row["event_id"]): (
                    int(row["origin_sequence"]),
                    str(row["payload_sha256"]).lower(),
                )
                for row in journal_rows
            }
            archive = {
                str(row["event_id"]): (
                    int(row["origin_sequence"]),
                    str(row["payload_sha256"]).lower(),
                    str(row["source_stream"]),
                    str(row["source_domain"]),
                )
                for row in archive_rows
            }
            missing_ids = set(journal) - set(archive)
            unexpected_ids = set(archive) - set(journal)
            metadata_mismatch_count = sum(
                1
                for event_id in set(journal) & set(archive)
                if journal[event_id][0] != archive[event_id][0]
                or journal[event_id][1] != archive[event_id][1]
                or archive[event_id][2] != expected_stream
                or archive[event_id][3] != expected_domain
            )
            duplicate_count = sum(
                int(row["duplicate_observation_count"])
                for row in archive_rows
            )
            archive_floor = contiguous_floor(
                [value[0] for value in archive.values()]
            )

            progress: dict[str, int] = {}
            for consumer_name in required_consumers:
                checkpoint = connection.execute(
                    "SELECT last_effect_sequence,last_ack_sequence,jetstream_ack_floor FROM consumer_checkpoints "
                    "WHERE consumer_name=? AND region=? AND generation=?",
                    (consumer_name, region, generation),
                ).fetchone()
                if checkpoint is None:
                    progress[consumer_name] = 0
                    expected_consumers_ok = False
                    continue
                effect_sequence = int(checkpoint["last_effect_sequence"])
                ack_sequence = int(checkpoint["last_ack_sequence"])
                js_floor = int(checkpoint["jetstream_ack_floor"])
                progress[consumer_name] = min(effect_sequence, ack_sequence)
                if not (
                    effect_sequence == ack_sequence == js_floor
                ):
                    expected_consumers_ok = False

            consumer_lag_count = sum(
                1
                for sequence in progress.values()
                if sequence < confirmed_watermark
            )
            expected_converged = (
                archive_floor >= confirmed_watermark
                and not missing_ids
                and not unexpected_ids
                and metadata_mismatch_count == 0
                and consumer_lag_count == 0
            )
            expected_region_convergence[region] = expected_converged

            actual = reconciliation["regions"][region]
            assert actual["status"] == (
                "CONVERGED" if expected_converged else "DIVERGED"
            )
            assert actual["journal_event_count"] == len(journal)
            assert actual["archive_event_count"] == len(archive)
            assert actual["missing_count"] == len(missing_ids)
            assert actual["unexpected_count"] == len(unexpected_ids)
            assert actual["duplicate_count"] == duplicate_count
            assert (
                actual["metadata_mismatch_count"]
                == metadata_mismatch_count
            )
            assert actual["consumer_lag_count"] == consumer_lag_count
            assert (
                actual["highest_contiguous_archive_origin_sequence"]
                == archive_floor
            )
            assert actual["required_consumer_progress"] == progress
            assert actual["converged"] is expected_converged

        expected_archive_ok = all(expected_region_convergence.values())
        expected_healthy = all(
            (
                expected_topology_ok,
                expected_generations_ok,
                expected_publication_ok,
                expected_archive_ok,
                expected_consumers_ok,
                expected_retention_ok,
                expected_recovery_ok,
            )
        )
        assert health["topology_ok"] is expected_topology_ok
        assert health["generations_ok"] is expected_generations_ok
        assert health["publication_ok"] is expected_publication_ok
        assert health["archive_ok"] is expected_archive_ok
        assert health["consumers_ok"] is expected_consumers_ok
        assert health["retention_ok"] is expected_retention_ok
        assert health["recovery_ok"] is expected_recovery_ok
        assert health["healthy"] is expected_healthy
        assert reconciliation["converged"] is expected_archive_ok

        assert (
            connection.execute(
                "SELECT COUNT(*) FROM event_journal"
            ).fetchone()[0]
            == 12000
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM consumer_checkpoints"
            ).fetchone()[0]
            >= 4
        )
        assert active_plans >= 1
    finally:
        connection.close()

    captured_incident_digests = {
        ROOT / "ops/stream-state.json": "763397e13b62c237dc37a0d1601a438e9a9247a681aaacb625f8f3425b154b1c",
        ROOT / "ops/shift-handoff.txt": "4a1b66e39bff8de9db528a0927fb37017a060aba4994c25939a0225fa8361be0",
        ROOT / "log/archive/inc-2026-0808-17-controller.log": "fc5a85713d9b963e18b7550048a11de16349c9daa260623f72aa33e6862fb7d6",
    }
    for captured_path, expected_digest in captured_incident_digests.items():
        assert captured_path.is_file()
        assert hashlib.sha256(captured_path.read_bytes()).hexdigest() == expected_digest


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
    """Generation, replay, lease and retention CLI paths remain wired, including a real replay publish."""
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
    assert any(
        plan["plan_id"] == planned["plan"]["plan_id"] for plan in listed
    )

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
    assert "safe_sequence" in retention
    assert "eligible_event_ids" in retention

    nats_config_dir = runtime_root / "config/nats"
    nats_config_dir.mkdir(parents=True, exist_ok=True)
    west_store = runtime_root / "state/nats/west"
    west_store.mkdir(parents=True, exist_ok=True)
    (nats_config_dir / "west.conf").write_text(
        "\n".join(
            (
                "server_name: EDGE-WEST-CONTRACT-TEST",
                "port: 4224",
                "http: 8224",
                "jetstream {",
                f'  store_dir: "{west_store}"',
                '  domain: "edge-west"',
                "  max_mem_store: 67108864",
                "  max_file_store: 268435456",
                "}",
                "",
            )
        ),
        encoding="utf-8",
    )
    manager = LabProcessManager(runtime_root)
    manager.start_one("west")
    try:
        manager.wait_monitor("http://127.0.0.1:8224", timeout=10)

        async def ensure_west_stream() -> None:
            pool = NatsConnectionPool()
            try:
                admin = JetStreamAdmin(pool, endpoints_from_engine(engine))
                await admin.upsert_stream(
                    "west",
                    str(engine.store.region("west")["physical_stream"]),
                    {
                        "subjects": ["telemetry.west.>"],
                        "retention": "limits",
                        "storage": "file",
                        "num_replicas": 1,
                        "duplicate_window": 120 * 1_000_000_000,
                        "max_age": 259200 * 1_000_000_000,
                        "allow_direct": False,
                        "deny_delete": True,
                        "deny_purge": True,
                    },
                )
            finally:
                await pool.close()

        asyncio.run(ensure_west_stream())
        expected_west_stream = str(engine.store.region("west")["physical_stream"])
        expected_replay_ids = {
            item.event_id
            for item in engine.store.replay_items("rp-west-incident-001")
            if engine.store.archive_record(item.event_id) is None
        }
        assert expected_replay_ids

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
        assert int(executed["published"]) >= 1

        async def read_west_stream_messages() -> tuple[object, list[object]]:
            pool = NatsConnectionPool()
            try:
                admin = JetStreamAdmin(pool, endpoints_from_engine(engine))
                snapshot = await admin.stream_info("west", expected_west_stream)
                messages = [
                    await admin.get_message_by_sequence(
                        "west", expected_west_stream, sequence
                    )
                    for sequence in range(
                        snapshot.first_sequence, snapshot.last_sequence + 1
                    )
                ]
                return snapshot, messages
            finally:
                await pool.close()

        west_snapshot, west_messages = asyncio.run(read_west_stream_messages())
        assert west_snapshot.name == expected_west_stream
        assert int(west_snapshot.messages) >= len(expected_replay_ids)
        observed_replay_ids: set[str] = set()
        for message in west_messages:
            document = json.loads(message.data.decode("utf-8"))
            event_id = str(document["event_id"])
            observed_replay_ids.add(event_id)
        assert expected_replay_ids <= observed_replay_ids

        replay_after = engine.store.replay_plan("rp-west-incident-001")
        assert (
            replay_after is not None
            and replay_after.status.value == "COMPLETED"
        )
        terminal_retention = engine.compute_retention_decision(
            region="west",
            generation=1,
            at=datetime(2026, 8, 9, 7, 30, tzinfo=UTC),
            limit=5,
        )
        assert terminal_retention.replay_pin_sequence is None

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
    finally:
        manager.stop_one("west")

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
        row["generation"] == 2 and row["status"] == "CONFIRMED"
        for row in generations
    )
