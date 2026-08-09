from __future__ import annotations

import json
import shutil
import sqlite3
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
        connection.executescript((ROOT / "sql/runtime_extensions.sql").read_text(encoding="utf-8"))
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
def contract_engine(tmp_path: Path, contract_baseline_database: Path) -> ContinuityEngine:
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


def _set_required_consumers(engine: ContinuityEngine, region: str, sequence: int) -> None:
    for consumer in engine.store.required_consumers():
        event_id = f"evt-{region}-g01-{sequence:06d}"
        engine.store.execute(
            "INSERT INTO consumer_checkpoints(consumer_name,region,generation,last_effect_sequence,last_ack_sequence,last_event_id,jetstream_ack_floor,updated_at) "
            "VALUES(?,?,1,?,?,?,?,?) ON CONFLICT(consumer_name,region,generation) DO UPDATE SET "
            "last_effect_sequence=excluded.last_effect_sequence,last_ack_sequence=excluded.last_ack_sequence,last_event_id=excluded.last_event_id,"
            "jetstream_ack_floor=excluded.jetstream_ack_floor,updated_at=excluded.updated_at",
            (consumer, region, sequence, sequence, event_id, sequence, "2026-08-09T00:00:00Z"),
        )


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


def test_f2p_final_health_and_reconciliation_reports_are_materialized() -> None:
    """The submitted repair leaves the requested operator JSON reports in the runtime output directory."""
    health_path = ROOT / "out/health.json"
    reconciliation_path = ROOT / "out/reconciliation.json"

    assert health_path.is_file(), "solution must materialize /app/continuity/out/health.json"
    assert reconciliation_path.is_file(), (
        "solution must materialize /app/continuity/out/reconciliation.json"
    )

    health = json.loads(health_path.read_text(encoding="utf-8"))
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))

    assert isinstance(health, dict)
    assert "healthy" in health and "details" in health
    assert isinstance(reconciliation, dict)
    assert "converged" in reconciliation and "regions" in reconciliation
    assert set(reconciliation["regions"]) == {"east", "west"}


# ---- P2P: already-correct detailed contract behavior ------------------------------------


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
