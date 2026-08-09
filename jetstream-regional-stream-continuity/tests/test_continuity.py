from __future__ import annotations

import asyncio
import json
import shutil
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

ROOT = Path("/app/continuity")
sys.path.insert(0, str(ROOT))

from continuity.engine import ContinuityEngine  # noqa: E402
from continuity.model import (  # noqa: E402
    ContractError,
    EffectStatus,
    EventEnvelope,
    EventIdentity,
    FencingError,
    GenerationStatus,
    PublishAck,
    ReplayConflict,
    ReplayRange,
    ReplayStatus,
    canonical_json,
    contiguous_floor,
    parse_iso,
    sha256_text,
)
from continuity.policy import OriginObservation  # noqa: E402
from continuity.store import ContinuityStore  # noqa: E402


class RecordingPublisher:
    def __init__(
        self,
        store: ContinuityStore,
        *,
        timeout: bool = False,
        ack_stream: str | None = None,
    ) -> None:
        self.store = store
        self.timeout = timeout
        self.ack_stream = ack_stream
        self.calls: list[dict[str, Any]] = []

    async def publish(
        self,
        event: EventEnvelope,
        *,
        message_id: str,
        expected_stream: str,
    ) -> PublishAck:
        self.calls.append(
            {
                "event_id": event.identity.event_id,
                "message_id": message_id,
                "expected_stream": expected_stream,
                "journal_state_during_publish": self.store.journal_state(
                    event.identity.event_id
                ).value,
            }
        )
        if self.timeout:
            raise TimeoutError("simulated publish timeout")
        return PublishAck(
            event_id=event.identity.event_id,
            stream=self.ack_stream or expected_stream,
            sequence=event.identity.origin_sequence,
            duplicate=False,
            acknowledged_at=datetime(2026, 8, 9, 0, 0, tzinfo=UTC),
        )


class FakeDelivery:
    def __init__(
        self,
        event: EventEnvelope,
        *,
        consumer_name: str = "telemetry-indexer",
        delivery_count: int = 1,
        ack_floor: int | None = None,
        fail_ack: bool = False,
    ) -> None:
        self.event = event
        self.consumer_name = consumer_name
        self.delivery_count = delivery_count
        self.jetstream_ack_floor = ack_floor or event.identity.origin_sequence
        self.fail_ack = fail_ack
        self.ack_calls = 0
        self.nak_calls = 0

    async def ack(self) -> None:
        self.ack_calls += 1
        if self.fail_ack:
            self.fail_ack = False
            raise RuntimeError("simulated crash at acknowledgement boundary")

    async def nak(self, delay_seconds: int | None = None) -> None:
        self.nak_calls += 1


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
def baseline_database(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("continuity-baseline") / "continuity.db"
    _build_database(path)
    return path


@pytest.fixture
def engine(tmp_path: Path, baseline_database: Path) -> ContinuityEngine:
    database = tmp_path / "continuity.db"
    shutil.copy2(baseline_database, database)
    store = ContinuityStore(database)
    return ContinuityEngine.from_json_file(store, ROOT / "config/continuity.json")


def sample_event(
    engine: ContinuityEngine, *, region: str = "east", sequence: int = 5700
) -> EventEnvelope:
    event = engine.store.event_by_origin(region, 1, sequence)
    assert event is not None
    return event


def complete_archive(engine: ContinuityEngine, region: str) -> None:
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


def set_checkpoint(
    engine: ContinuityEngine,
    consumer: str,
    region: str,
    *,
    effect: int,
    ack: int | None = None,
    js_floor: int | None = None,
) -> None:
    ack_value = effect if ack is None else ack
    js_value = ack_value if js_floor is None else js_floor
    event_id = f"evt-{region}-g01-{max(effect, 1):06d}"
    engine.store.execute(
        "INSERT INTO consumer_checkpoints(consumer_name,region,generation,last_effect_sequence,last_ack_sequence,last_event_id,jetstream_ack_floor,updated_at) "
        "VALUES(?,?,1,?,?,?,?,?) ON CONFLICT(consumer_name,region,generation) DO UPDATE SET "
        "last_effect_sequence=excluded.last_effect_sequence,last_ack_sequence=excluded.last_ack_sequence,last_event_id=excluded.last_event_id,"
        "jetstream_ack_floor=excluded.jetstream_ack_floor,updated_at=excluded.updated_at",
        (
            consumer,
            region,
            effect,
            ack_value,
            event_id,
            js_value,
            "2026-08-09T00:00:00Z",
        ),
    )


def finding_types(summary: Any) -> set[str]:
    return {finding.finding_type for finding in summary.findings}


def dispatch_count(engine: ContinuityEngine, consumer: str, event_id: str) -> int:
    return int(
        engine.store.scalar(
            "SELECT COUNT(*) FROM effect_dispatches WHERE consumer_name=? AND event_id=? AND state='CONFIRMED'",
            (consumer, event_id),
        )
        or 0
    )


# ---- F2P: identity and publish durability -------------------------------------------------


def test_f2p_retry_uses_stable_event_id(engine: ContinuityEngine) -> None:
    """Publish retries keep the accepted event id as the JetStream message id."""
    event = sample_event(engine)
    assert engine.message_id_for_event(event, attempt_no=1) == event.identity.event_id
    assert engine.message_id_for_event(event, attempt_no=9) == event.identity.event_id


def test_f2p_reconnect_retry_does_not_mint_new_identity(
    engine: ContinuityEngine,
) -> None:
    """A delayed reconnect retry has the same idempotency identity as the original send."""
    event = sample_event(engine, region="west", sequence=5750)
    first = engine.message_id_for_event(event, attempt_no=1)
    delayed = engine.message_id_for_event(event, attempt_no=17)
    assert first == delayed == event.identity.event_id


def test_f2p_publish_failure_does_not_mark_journal_published(
    engine: ContinuityEngine,
) -> None:
    """The journal remains PUBLISHING until a positive publish acknowledgement exists."""
    event = sample_event(engine, sequence=5990)
    publisher = RecordingPublisher(engine.store, timeout=True)
    with pytest.raises(TimeoutError):
        asyncio.run(engine.publish_event(event.identity.event_id, publisher))
    assert publisher.calls[0]["journal_state_during_publish"] == "PUBLISHING"
    assert engine.store.journal_state(event.identity.event_id).value == "RETRY"


def test_f2p_publish_ack_transitions_journal_once(engine: ContinuityEngine) -> None:
    """Only an acknowledgement for the expected physical stream may publish a journal row."""
    event = sample_event(engine, sequence=5985)
    expected_stream = str(engine.store.region("east")["physical_stream"])
    publisher = RecordingPublisher(engine.store)
    ack = asyncio.run(engine.publish_event(event.identity.event_id, publisher))
    assert publisher.calls[0]["journal_state_during_publish"] == "PUBLISHING"
    assert publisher.calls[0]["message_id"] == event.identity.event_id
    assert ack.stream == expected_stream
    assert engine.store.journal_state(event.identity.event_id).value == "PUBLISHED"

    wrong_event = sample_event(engine, sequence=5984)
    wrong_stream = str(engine.store.region("west")["physical_stream"])
    wrong_publisher = RecordingPublisher(engine.store, ack_stream=wrong_stream)
    with pytest.raises(ContractError):
        asyncio.run(engine.publish_event(wrong_event.identity.event_id, wrong_publisher))
    assert wrong_publisher.calls[0]["journal_state_during_publish"] == "PUBLISHING"
    assert engine.store.journal_state(wrong_event.identity.event_id).value == "RETRY"
    attempt = engine.store.publish_attempts(wrong_event.identity.event_id)[-1]
    assert attempt["outcome"] == "ERROR"
    assert attempt["requested_stream"] == expected_stream
    assert attempt["message_id"] == wrong_event.identity.event_id


# ---- F2P: origin generation ---------------------------------------------------------------


def test_f2p_generation_regression_is_held(engine: ContinuityEngine) -> None:
    """A changed origin fingerprint becomes pending instead of replacing the confirmed generation."""
    current = engine.store.confirmed_generation("west")
    assert current is not None
    observation = OriginObservation(
        region="west",
        stream_name=str(engine.region_config("west")["stream_name"]),
        domain=str(engine.region_config("west")["domain"]),
        stream_fingerprint="west-recreated-9f3a",
        first_sequence=1,
        last_sequence=42,
        observed_at=datetime(2026, 8, 9, 1, 0, tzinfo=UTC),
    )
    result = engine.validate_origin_observation(observation)
    assert result.generation == current.generation + 1
    assert result.status is GenerationStatus.PENDING_APPROVAL
    still_current = engine.store.confirmed_generation("west")
    assert still_current is not None and still_current.generation == current.generation


def test_f2p_generation_header_mismatch_is_rejected(engine: ContinuityEngine) -> None:
    """Events from a newly observed generation remain ineligible until the generation is approved."""
    observation = OriginObservation(
        region="west",
        stream_name=str(engine.region_config("west")["stream_name"]),
        domain=str(engine.region_config("west")["domain"]),
        stream_fingerprint="west-new-incarnation-aa91",
        first_sequence=1,
        last_sequence=10,
        observed_at=datetime(2026, 8, 9, 1, 5, tzinfo=UTC),
    )
    pending = engine.validate_origin_observation(observation)
    event = EventEnvelope.from_mapping(
        {
            "event_id": "evt-west-g02-000001",
            "region": "west",
            "origin_generation": 2,
            "origin_sequence": 1,
            "device_id": "dev-west-001",
            "site_id": "site-01",
            "event_type": "pressure.sample",
            "event_time": "2026-08-09T01:05:00Z",
            "accepted_at": "2026-08-09T01:05:01Z",
            "payload": {"reading": 101},
            "payload_sha256": sha256_text(canonical_json({"reading": 101})),
            "payload_bytes": 64,
            "priority": 5,
        }
    )
    assert pending.status is GenerationStatus.PENDING_APPROVAL
    with pytest.raises(Exception):
        engine.validate_event_generation(event)


# ---- F2P: stream/source topology ----------------------------------------------------------


def test_f2p_hub_raw_archive_rejects_local_subject_write(
    engine: ContinuityEngine,
) -> None:
    """The hub raw archive is source-only and exposes no local raw listen subject."""
    topology = engine.topology()
    assert topology.hub_archive.subjects == ()


def test_f2p_stream_catalog_uses_unique_physical_names(
    engine: ContinuityEngine,
) -> None:
    """East, west and hub physical stream names are unique in the connected topology."""
    topology = engine.topology()
    names = [
        topology.hub_archive.name,
        *[stream.name for stream in topology.edge_streams.values()],
    ]
    assert len(names) == len(set(names))
    assert (
        topology.edge_streams["east"].name
        == engine.store.region("east")["physical_stream"]
    )
    assert (
        topology.edge_streams["west"].name
        == engine.store.region("west")["physical_stream"]
    )


def test_f2p_source_domains_match_edge_ownership(engine: ContinuityEngine) -> None:
    """Every hub source points at the stream/domain that owns that region."""
    topology = engine.topology()
    assert topology.source_for("east").origin.domain == "edge-east"
    assert topology.source_for("west").origin.domain == "edge-west"
    assert topology.source_for("east").origin.name == "EDGE_EAST_TELEMETRY"
    assert topology.source_for("west").origin.name == "EDGE_WEST_TELEMETRY"


def test_f2p_archive_metadata_preserves_origin_identity(
    engine: ContinuityEngine,
) -> None:
    """A matching event id with corrupted source ownership is reported as divergent."""
    complete_archive(engine, "east")
    event = sample_event(engine, sequence=120)
    engine.store.execute(
        "UPDATE archive_index SET source_domain='edge-west' WHERE event_id=?",
        (event.identity.event_id,),
    )
    summary = engine.reconcile_region("east", 1)
    assert summary.metadata_mismatch_count == 1
    assert summary.highest_contiguous_archive_origin_sequence == 6000
    assert summary.converged is False
    assert any(
        finding.event_id == event.identity.event_id
        for finding in summary.blocking_findings
    )


# ---- F2P: consumer processing -------------------------------------------------------------


def test_f2p_redelivery_creates_single_effect(engine: ContinuityEngine) -> None:
    """Redelivery may revalidate an event but emits the downstream effect only once."""
    event = sample_event(engine, sequence=5700)
    engine.store.execute(
        "DELETE FROM processing_effects WHERE consumer_name='telemetry-indexer' AND event_id=?",
        (event.identity.event_id,),
    )
    first = FakeDelivery(event, delivery_count=1)
    second = FakeDelivery(event, delivery_count=2)
    asyncio.run(engine.process_delivery(first, worker_id="w1", fence_epoch=1))
    asyncio.run(engine.process_delivery(second, worker_id="w2", fence_epoch=1))
    assert dispatch_count(engine, "telemetry-indexer", event.identity.event_id) == 1
    effect = engine.store.effect("telemetry-indexer", event.identity.event_id)
    assert effect is not None and effect.status is EffectStatus.COMMITTED


def test_f2p_crash_after_effect_before_ack_is_idempotent(
    engine: ContinuityEngine,
) -> None:
    """A crash after effect commit but before ack does not emit the effect again after redelivery."""
    event = sample_event(engine, sequence=5699)
    engine.store.execute(
        "DELETE FROM processing_effects WHERE consumer_name='telemetry-indexer' AND event_id=?",
        (event.identity.event_id,),
    )
    crashing = FakeDelivery(event, delivery_count=1, fail_ack=True)
    with pytest.raises(RuntimeError):
        asyncio.run(
            engine.process_delivery(crashing, worker_id="crash-worker", fence_epoch=1)
        )
    redelivery = FakeDelivery(event, delivery_count=2)
    asyncio.run(
        engine.process_delivery(redelivery, worker_id="restart-worker", fence_epoch=1)
    )
    assert dispatch_count(engine, "telemetry-indexer", event.identity.event_id) == 1


def test_f2p_checkpoint_does_not_advance_before_effect_commit(
    engine: ContinuityEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed effect commit cannot leave the application acknowledgement checkpoint ahead."""
    event = sample_event(engine, sequence=5698)
    engine.store.execute(
        "DELETE FROM processing_effects WHERE consumer_name='telemetry-indexer' AND event_id=?",
        (event.identity.event_id,),
    )
    before = engine.store.checkpoint("telemetry-indexer", "east", 1)
    assert before is not None

    def fail_commit(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("simulated effect store failure")

    monkeypatch.setattr(engine.store, "commit_effect", fail_commit)
    with pytest.raises(RuntimeError):
        asyncio.run(
            engine.process_delivery(
                FakeDelivery(event, delivery_count=1),
                worker_id="fault-worker",
                fence_epoch=1,
            )
        )
    after = engine.store.checkpoint("telemetry-indexer", "east", 1)
    assert after is not None
    assert after.last_ack_sequence == before.last_ack_sequence


def test_f2p_poison_event_is_quarantined_without_completion(
    engine: ContinuityEngine,
) -> None:
    """Quarantine records audit evidence without committing or dispatching a business effect."""
    event = sample_event(engine, sequence=5680)
    consumer = "safety-state-projector"
    engine.store.execute(
        "DELETE FROM processing_effects WHERE consumer_name=? AND event_id=?",
        (consumer, event.identity.event_id),
    )
    engine.store.execute(
        "DELETE FROM effect_dispatches WHERE consumer_name=? AND event_id=?",
        (consumer, event.identity.event_id),
    )
    before = engine.store.checkpoint(consumer, "east", 1)
    assert before is not None
    result = asyncio.run(
        engine.process_delivery(
            FakeDelivery(event, consumer_name=consumer, delivery_count=5),
            worker_id="safety-worker",
            fence_epoch=1,
            poison_predicate=lambda _: True,
        )
    )
    after = engine.store.checkpoint(consumer, "east", 1)
    effect = engine.store.effect(consumer, event.identity.event_id)
    assert after is not None
    assert result.status == "QUARANTINED"
    assert effect is not None and effect.status is EffectStatus.QUARANTINED
    assert dispatch_count(engine, consumer, event.identity.event_id) == 0
    assert after.last_effect_sequence == before.last_effect_sequence
    assert after.last_ack_sequence == before.last_ack_sequence


def test_f2p_restart_detects_ack_floor_effect_ledger_gap(
    engine: ContinuityEngine,
) -> None:
    """Health remains degraded when JetStream ack floor is ahead of durable application effects."""
    set_checkpoint(
        engine, "telemetry-indexer", "east", effect=5600, ack=5600, js_floor=5650
    )
    ok, details = engine.consumer_health()
    assert ok is False
    east = next(
        item for item in details["telemetry-indexer"] if item["region"] == "east"
    )
    assert east["state_gap"] == 50


# ---- F2P: reconciliation -----------------------------------------------------------------


def test_f2p_reconcile_ignores_hub_sequence_equivalence(
    engine: ContinuityEngine,
) -> None:
    """Stable origin completeness and reported progress are independent of hub delivery positions."""
    complete_archive(engine, "east")
    for consumer in engine.store.required_consumers():
        set_checkpoint(engine, consumer, "east", effect=6000)

    engine.store.execute(
        "UPDATE origin_generations SET last_observed_sequence=60002 "
        "WHERE region='east' AND generation=1"
    )
    engine.store.execute(
        "UPDATE archive_index SET hub_stream_sequence=30000+origin_sequence "
        "WHERE region='east' AND generation=1"
    )

    for offset, source_event_id in enumerate(
        ("evt-east-g01-000101", "evt-east-g01-000102", "evt-east-g01-000103")
    ):
        origin_sequence = 60000 + offset
        event_id = f"evt-east-g01-{origin_sequence:06d}"
        engine.store.execute(
            "INSERT INTO event_journal("
            "journal_id,event_id,region,generation,origin_sequence,device_id,site_id,event_type,event_time,accepted_at,"
            "payload_json,payload_sha256,payload_bytes,priority,publish_state,publish_attempts,last_publish_at,publish_ack_stream,"
            "publish_ack_sequence,archive_confirmed_at,retention_hold) "
            "SELECT ?,?,'east',1,?,device_id,site_id,event_type,event_time,accepted_at,payload_json,payload_sha256,payload_bytes,priority,"
            "'ARCHIVED',1,accepted_at,'EDGE_EAST_TELEMETRY',?,accepted_at,0 FROM event_journal WHERE event_id=?",
            (
                900000 + offset,
                event_id,
                origin_sequence,
                origin_sequence,
                source_event_id,
            ),
        )
        engine.store.execute(
            "INSERT INTO archive_index(event_id,region,generation,origin_sequence,hub_stream_sequence,payload_sha256,archived_at,source_stream,source_domain,duplicate_observation_count) "
            "SELECT event_id,'east',1,origin_sequence,?,payload_sha256,accepted_at,'EDGE_EAST_TELEMETRY','edge-east',0 "
            "FROM event_journal WHERE event_id=?",
            (50000 + offset, event_id),
        )

    summary = engine.reconcile_region("east", 1)
    assert summary.journal_event_count == 6003
    assert summary.archive_event_count == 6003
    assert summary.missing_count == 0
    assert summary.unexpected_count == 0
    assert summary.metadata_mismatch_count == 0
    assert summary.consumer_lag_count == 0
    assert summary.highest_contiguous_archive_origin_sequence == 6000
    assert summary.required_consumer_progress == {
        consumer: 6000 for consumer in engine.store.required_consumers()
    }
    assert summary.converged is True


def test_f2p_reconcile_finds_offsetting_gap_and_duplicate(
    engine: ContinuityEngine,
) -> None:
    """Equal counts still expose the missing and unexpected stable identities."""
    complete_archive(engine, "east")
    missing = "evt-east-g01-000123"
    unexpected = "evt-east-g01-999999"
    engine.store.execute("DELETE FROM archive_index WHERE event_id=?", (missing,))
    engine.store.execute(
        "INSERT INTO archive_index(event_id,region,generation,origin_sequence,hub_stream_sequence,payload_sha256,archived_at,source_stream,source_domain,duplicate_observation_count) "
        "VALUES(?,'east',1,999999,9999999,?,'2026-08-09T00:00:00Z','EDGE_EAST_TELEMETRY','edge-east',0)",
        (unexpected, "f" * 64),
    )
    summary = engine.reconcile_region("east", 1)
    assert summary.journal_event_count == summary.archive_event_count
    assert summary.missing_count == 1
    assert summary.unexpected_count == 1
    assert summary.highest_contiguous_archive_origin_sequence == 122
    assert summary.converged is False
    blocking_ids = {
        finding.event_id
        for finding in summary.blocking_findings
        if finding.event_id is not None
    }
    assert {missing, unexpected} <= blocking_ids


def test_f2p_convergence_waits_for_all_required_consumers(
    engine: ContinuityEngine,
) -> None:
    """A complete archive reports required-consumer progress and waits for the slowest application."""
    complete_archive(engine, "east")
    set_checkpoint(engine, "telemetry-indexer", "east", effect=6000)
    set_checkpoint(engine, "safety-state-projector", "east", effect=5999)
    summary = engine.reconcile_region("east", 1)
    assert summary.converged is False
    assert summary.consumer_lag_count >= 1
    assert summary.highest_contiguous_archive_origin_sequence == 6000
    assert summary.required_consumer_progress["telemetry-indexer"] == 6000
    assert summary.required_consumer_progress["safety-state-projector"] == 5999


# ---- F2P: replay -------------------------------------------------------------------------


def test_f2p_replay_plan_contains_only_missing_events(engine: ContinuityEngine) -> None:
    """Replay planning selects exact missing identities and permits a later disjoint active gap."""
    complete_archive(engine, "east")
    first_missing = {"evt-east-g01-005800", "evt-east-g01-005801"}
    for event_id in first_missing:
        engine.store.execute("DELETE FROM archive_index WHERE event_id=?", (event_id,))

    first = engine.plan_replay(
        region="east",
        generation=1,
        created_by="verifier",
        reason="first isolated reconciliation gap",
        approve=True,
        approved_by="shift-lead",
    )
    assert first.plan is not None
    assert set(first.plan.event_ids) == first_missing
    assert set(first.missing_event_ids) == first_missing
    assert first.plan.replay_range == ReplayRange("east", 1, 5800, 5801)

    complete_archive(engine, "east")
    second_missing = {"evt-east-g01-005900", "evt-east-g01-005901"}
    for event_id in second_missing:
        engine.store.execute("DELETE FROM archive_index WHERE event_id=?", (event_id,))

    second = engine.plan_replay(
        region="east",
        generation=1,
        created_by="verifier",
        reason="second disjoint reconciliation gap",
        approve=True,
        approved_by="shift-lead",
    )
    assert second.plan is not None
    assert set(second.plan.event_ids) == second_missing
    assert set(second.missing_event_ids) == second_missing
    assert first.plan.replay_range.overlaps(second.plan.replay_range) is False


def test_f2p_replay_refuses_unapproved_generation(engine: ContinuityEngine) -> None:
    """Recovery planning cannot cross into a generation awaiting operator approval."""
    engine.store.record_pending_generation(
        "east",
        generation=2,
        stream_fingerprint="east-pending-002",
        first_sequence=1,
        last_observed_sequence=10,
        at=datetime(2026, 8, 9, 2, 0, tzinfo=UTC),
    )
    decision = engine.plan_replay(
        region="east",
        generation=2,
        created_by="verifier",
        reason="must remain held",
    )
    assert decision.plan is None
    assert decision.blocked_reason is not None


def test_f2p_delayed_retry_dedupes_beyond_server_window(
    engine: ContinuityEngine,
) -> None:
    """Durable archive/effect identity prevents duplicates after server-side dedupe is no longer authority."""
    event = sample_event(engine, region="west", sequence=5800)
    engine.store.execute(
        "DELETE FROM processing_effects WHERE consumer_name='telemetry-indexer' AND event_id=?",
        (event.identity.event_id,),
    )
    engine.store.execute(
        "DELETE FROM effect_dispatches WHERE consumer_name='telemetry-indexer' AND event_id=?",
        (event.identity.event_id,),
    )

    asyncio.run(
        engine.process_delivery(
            FakeDelivery(event, delivery_count=1),
            worker_id="first-window-worker",
            fence_epoch=1,
        )
    )
    asyncio.run(
        engine.process_delivery(
            FakeDelivery(event, delivery_count=300),
            worker_id="post-window-worker",
            fence_epoch=1,
        )
    )

    assert dispatch_count(engine, "telemetry-indexer", event.identity.event_id) == 1
    assert (
        int(
            engine.store.scalar(
                "SELECT COUNT(*) FROM processing_effects WHERE consumer_name=? AND event_id=?",
                ("telemetry-indexer", event.identity.event_id),
            )
            or 0
        )
        == 1
    )
    effect = engine.store.effect("telemetry-indexer", event.identity.event_id)
    assert effect is not None and effect.status is EffectStatus.COMMITTED

    complete_archive(engine, "west")
    archive_before = engine.store.archive_record(event.identity.event_id)
    assert archive_before is not None
    assert engine.store.upsert_archive_record(archive_before) is False
    assert (
        int(
            engine.store.scalar(
                "SELECT COUNT(*) FROM archive_index WHERE event_id=?",
                (event.identity.event_id,),
            )
            or 0
        )
        == 1
    )

    ids = {engine.message_id_for_event(event, attempt_no=n) for n in (1, 2, 30, 300)}
    assert ids == {event.identity.event_id}


# ---- F2P: retention ----------------------------------------------------------------------


def test_f2p_cleanup_stops_at_archive_watermark(engine: ContinuityEngine) -> None:
    """Cleanup cannot cross the highest contiguous archived origin sequence."""
    archive_sequences = [
        record.identity.origin_sequence
        for record in engine.store.iter_archive(region="east", generation=1)
    ]
    expected_floor = contiguous_floor(archive_sequences)
    decision = engine.compute_retention_decision(region="east", generation=1)
    assert decision.safe_sequence <= expected_floor


def test_f2p_cleanup_stops_at_slowest_required_consumer(
    engine: ContinuityEngine,
) -> None:
    """Cleanup uses the slowest required application consumer as a hard upper bound."""
    decision = engine.compute_retention_decision(region="east", generation=1)
    slowest = engine.store.slowest_required_consumer_sequence("east", 1)
    assert decision.safe_sequence <= slowest


def test_f2p_cleanup_preserves_rows_for_active_replay_plan(
    engine: ContinuityEngine,
) -> None:
    """An approved replay plan pins its source journal rows against cleanup."""
    decision = engine.compute_retention_decision(region="west", generation=1)
    assert decision.replay_pin_sequence == 5311
    assert decision.safe_sequence <= 5310


def test_f2p_retention_policy_covers_recovery_horizon(engine: ContinuityEngine) -> None:
    """Both edge and hub raw stream ages cover disconnect plus replay plus safety margin."""
    policy = engine.retention_policy("east")
    assert (
        engine.edge_stream_policy("east").max_age_seconds
        >= policy.required_horizon_seconds
    )
    assert (
        engine.edge_stream_policy("west").max_age_seconds
        >= policy.required_horizon_seconds
    )
    assert engine.hub_stream_policy().max_age_seconds >= policy.required_horizon_seconds


# ---- F2P: fencing and routing -------------------------------------------------------------


def test_f2p_stale_recovery_worker_is_fenced(engine: ContinuityEngine) -> None:
    """Replay rejects a stale token at entry and revalidates fencing between applied items."""
    now = datetime.now(UTC)
    first = engine.acquire_recovery_lease(
        region="east",
        owner_id="worker-a",
        ttl_seconds=300,
        at=now,
    )
    current = engine.store.write_lease(
        region="east",
        owner_id="worker-a",
        fence_epoch=first.fence_epoch + 1,
        acquired_at=now,
        renewed_at=now + timedelta(seconds=1),
        expires_at=now + timedelta(minutes=5),
    )
    assert current.fence_epoch > first.fence_epoch

    entry_event = "evt-east-g01-005999"
    entry_plan = engine.store.insert_replay_plan(
        plan_id="stale-fence-entry",
        replay_range=ReplayRange("east", 1, 5999, 5999),
        status=ReplayStatus.APPROVED,
        reason="verify stale execution fencing at entry",
        created_by="verifier",
        event_ids=[entry_event],
        approved_by="shift-lead",
        approved_at=now,
    )
    with pytest.raises(FencingError):
        asyncio.run(
            engine.execute_replay_plan(
                entry_plan.plan_id,
                owner_id="worker-a",
                fence_epoch=first.fence_epoch,
                publisher=RecordingPublisher(engine.store),
            )
        )
    after_entry = engine.store.replay_plan(entry_plan.plan_id)
    assert after_entry is not None and after_entry.status is ReplayStatus.APPROVED

    west_lease = engine.acquire_recovery_lease(
        region="west",
        owner_id="worker-mid-plan",
        ttl_seconds=300,
        at=now,
    )
    mid_ids = ["evt-west-g01-005998", "evt-west-g01-005999"]
    for event_id in mid_ids:
        engine.store.execute("DELETE FROM archive_index WHERE event_id=?", (event_id,))
    mid_plan = engine.store.insert_replay_plan(
        plan_id="stale-fence-mid-plan",
        replay_range=ReplayRange("west", 1, 5998, 5999),
        status=ReplayStatus.APPROVED,
        reason="verify fence revalidation between replay items",
        created_by="verifier",
        event_ids=mid_ids,
        approved_by="shift-lead",
        approved_at=now,
    )

    class FenceRotatingPublisher(RecordingPublisher):
        async def publish(
            self,
            event: EventEnvelope,
            *,
            message_id: str,
            expected_stream: str,
        ) -> PublishAck:
            ack = await super().publish(
                event,
                message_id=message_id,
                expected_stream=expected_stream,
            )
            if len(self.calls) == 1:
                lease = engine.store.current_lease("west")
                assert lease is not None
                rotated_at = datetime.now(UTC)
                engine.store.write_lease(
                    region="west",
                    owner_id=lease.owner_id,
                    fence_epoch=lease.fence_epoch + 1,
                    acquired_at=lease.acquired_at,
                    renewed_at=rotated_at,
                    expires_at=rotated_at + timedelta(minutes=5),
                )
            return ack

    publisher = FenceRotatingPublisher(engine.store)
    outcome = asyncio.run(
        engine.execute_replay_plan(
            mid_plan.plan_id,
            owner_id=west_lease.owner_id,
            fence_epoch=west_lease.fence_epoch,
            publisher=publisher,
        )
    )
    items = {
        item.event_id: item for item in engine.store.replay_items(mid_plan.plan_id)
    }
    assert len(publisher.calls) == 1
    assert items[mid_ids[0]].state == "PUBLISHED"
    assert items[mid_ids[1]].state == "HELD"
    assert outcome.published == 1
    assert outcome.held == 1
    assert outcome.completed is False


def test_f2p_overlapping_active_replay_plan_is_rejected(
    engine: ContinuityEngine,
) -> None:
    """A new west replay cannot overlap the already approved incident replay range."""
    with pytest.raises(ReplayConflict):
        engine.plan_replay(
            region="west",
            generation=1,
            created_by="verifier",
            reason="second recovery planner",
        )


def test_f2p_derived_output_never_reenters_raw_archive(
    engine: ContinuityEngine,
) -> None:
    """Derived consumer output is outside the raw sourced telemetry namespace."""
    event = sample_event(engine)
    subject = engine.derived_subject_for(event, consumer_name="telemetry-indexer")
    assert subject.startswith("telemetry.derived.")
    assert not subject.startswith("telemetry.raw.")


# ---- P2P: preserve already-correct behavior ----------------------------------------------


def test_p2p_distinct_same_payload_events_remain_distinct(
    engine: ContinuityEngine,
) -> None:
    """Two legitimate repeated readings remain distinct when their event identities differ."""
    first = sample_event(engine, sequence=100)
    second = sample_event(engine, sequence=101)
    payload = {"reading": 77, "quality": "GOOD"}
    digest = sha256_text(canonical_json(payload))
    a = EventEnvelope(
        identity=first.identity,
        device_id=first.device_id,
        site_id=first.site_id,
        event_type=first.event_type,
        event_time=first.event_time,
        accepted_at=first.accepted_at,
        payload=payload,
        payload_sha256=digest,
        payload_bytes=64,
        priority=first.priority,
    )
    b = EventEnvelope(
        identity=second.identity,
        device_id=second.device_id,
        site_id=second.site_id,
        event_type=second.event_type,
        event_time=second.event_time,
        accepted_at=second.accepted_at,
        payload=payload,
        payload_sha256=digest,
        payload_bytes=64,
        priority=second.priority,
    )
    assert a.payload_sha256 == b.payload_sha256
    assert a.identity.event_id != b.identity.event_id
    assert a.message_id != b.message_id


def test_p2p_confirmed_generation_continues_monotonically(
    engine: ContinuityEngine,
) -> None:
    """A matching origin fingerprint extends the current generation without creating a new one."""
    current = engine.store.confirmed_generation("east")
    assert current is not None
    result = engine.validate_origin_observation(
        OriginObservation(
            region="east",
            stream_name=str(engine.region_config("east")["stream_name"]),
            domain=str(engine.region_config("east")["domain"]),
            stream_fingerprint=current.stream_fingerprint,
            first_sequence=current.last_observed_sequence,
            last_sequence=current.last_observed_sequence + 50,
            observed_at=datetime(2026, 8, 9, 4, 0, tzinfo=UTC),
        )
    )
    assert result.generation == current.generation
    assert result.status is GenerationStatus.CONFIRMED
    assert result.last_observed_sequence >= current.last_observed_sequence + 50


def test_p2p_successful_effect_advances_checkpoint(engine: ContinuityEngine) -> None:
    """A successful first delivery commits its effect and advances both application checkpoints."""
    event = sample_event(engine, sequence=5675)
    engine.store.execute(
        "DELETE FROM processing_effects WHERE consumer_name='telemetry-indexer' AND event_id=?",
        (event.identity.event_id,),
    )
    result = asyncio.run(
        engine.process_delivery(
            FakeDelivery(event, delivery_count=1),
            worker_id="normal-worker",
            fence_epoch=1,
        )
    )
    assert result.status == "COMMITTED"
    checkpoint = engine.store.checkpoint("telemetry-indexer", "east", 1)
    assert checkpoint is not None
    assert checkpoint.last_effect_sequence >= event.identity.origin_sequence
    assert checkpoint.last_ack_sequence >= event.identity.origin_sequence


def test_p2p_fully_converged_old_rows_are_cleanup_eligible(
    engine: ContinuityEngine,
) -> None:
    """Old journal rows become eligible once archive and all required consumers are safely ahead."""
    complete_archive(engine, "east")
    set_checkpoint(engine, "telemetry-indexer", "east", effect=6000)
    set_checkpoint(engine, "safety-state-projector", "east", effect=6000)
    engine.store.execute(
        "UPDATE event_journal SET retention_hold=0,accepted_at='2026-08-01T00:00:00Z' WHERE region='east' AND origin_sequence<=100"
    )
    decision = engine.compute_retention_decision(
        region="east",
        generation=1,
        at=datetime(2026, 8, 9, 5, 0, tzinfo=UTC),
        limit=200,
    )
    assert decision.safe_sequence >= 100
    assert any(event_id.endswith("000100") for event_id in decision.eligible_event_ids)


def test_p2p_current_lease_owner_can_renew_same_epoch(engine: ContinuityEngine) -> None:
    """Current-token renewal succeeds, while the same owner with a stale epoch cannot mutate the lease."""
    t0 = datetime(2026, 8, 9, 6, 0, tzinfo=UTC)
    first = engine.acquire_recovery_lease(
        region="west", owner_id="worker-a", ttl_seconds=30, at=t0
    )
    renewed = engine.renew_recovery_lease(
        region="west",
        owner_id="worker-a",
        fence_epoch=first.fence_epoch,
        ttl_seconds=30,
        at=t0 + timedelta(seconds=10),
    )
    assert renewed.fence_epoch == first.fence_epoch
    assert renewed.expires_at > first.expires_at

    rotated_at = t0 + timedelta(seconds=11)
    current = engine.store.write_lease(
        region="west",
        owner_id="worker-a",
        fence_epoch=renewed.fence_epoch + 1,
        acquired_at=renewed.acquired_at,
        renewed_at=rotated_at,
        expires_at=rotated_at + timedelta(seconds=45),
    )
    with pytest.raises(FencingError):
        engine.renew_recovery_lease(
            region="west",
            owner_id="worker-a",
            fence_epoch=renewed.fence_epoch,
            ttl_seconds=300,
            at=rotated_at + timedelta(seconds=1),
        )
    after = engine.store.current_lease("west")
    assert after is not None
    assert after.fence_epoch == current.fence_epoch
    assert after.expires_at == current.expires_at
