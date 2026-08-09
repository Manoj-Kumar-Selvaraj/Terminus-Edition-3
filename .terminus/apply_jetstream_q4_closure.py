#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from pathlib import Path

TASK = Path("jetstream-regional-stream-continuity")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_tests() -> None:
    path = TASK / "tests/test_continuity.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from continuity.policy import OriginObservation  # noqa: E402\nfrom continuity.store import ContinuityStore  # noqa: E402\n",
        """from continuity.policy import OriginObservation  # noqa: E402
from continuity.runtime import (  # noqa: E402
    JetStreamAdmin,
    LabProcessManager,
    NatsConnectionPool,
    NatsPublisher,
    endpoints_from_engine,
)
from continuity.store import ContinuityStore  # noqa: E402
""",
        "runtime import",
    )

    text = replace_once(
        text,
        '''def test_f2p_retry_uses_stable_event_id(engine: ContinuityEngine) -> None:
    """Publish retries keep the accepted event id as the JetStream message id."""
    event = sample_event(engine)
    assert engine.message_id_for_event(event, attempt_no=1) == event.identity.event_id
    assert engine.message_id_for_event(event, attempt_no=9) == event.identity.event_id
''',
        '''def test_f2p_retry_uses_stable_event_id(
    engine: ContinuityEngine, tmp_path: Path
) -> None:
    """Replay publishes expose the stable event id as the physical JetStream message id."""
    runtime_root = tmp_path / "stable-replay-identity"
    nats_config_dir = runtime_root / "config/nats"
    west_store = runtime_root / "state/nats/west"
    nats_config_dir.mkdir(parents=True)
    west_store.mkdir(parents=True)
    (nats_config_dir / "west.conf").write_text(
        "\\n".join(
            (
                "server_name: EDGE-WEST-F2P-IDENTITY",
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

    expected_stream = str(engine.store.region("west")["physical_stream"])
    expected_replay_ids = {
        item.event_id
        for item in engine.store.replay_items("rp-west-incident-001")
        if engine.store.archive_record(item.event_id) is None
    }
    assert expected_replay_ids

    manager = LabProcessManager(runtime_root)
    manager.start_one("west")
    try:
        manager.wait_monitor("http://127.0.0.1:8224", timeout=10)
        lease = engine.acquire_recovery_lease(
            region="west",
            owner_id="f2p-stable-identity-worker",
            ttl_seconds=300,
            at=datetime.now(UTC),
        )

        async def publish_and_observe() -> tuple[object, list[object]]:
            pool = NatsConnectionPool()
            try:
                endpoints = endpoints_from_engine(engine)
                admin = JetStreamAdmin(pool, endpoints)
                await admin.upsert_stream(
                    "west",
                    expected_stream,
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
                outcome = await engine.execute_replay_plan(
                    "rp-west-incident-001",
                    owner_id="f2p-stable-identity-worker",
                    fence_epoch=lease.fence_epoch,
                    publisher=NatsPublisher(pool, endpoints["west"]),
                )
                snapshot = await admin.stream_info("west", expected_stream)
                messages = [
                    await admin.get_message_by_sequence(
                        "west", expected_stream, sequence
                    )
                    for sequence in range(
                        snapshot.first_sequence, snapshot.last_sequence + 1
                    )
                ]
                return outcome, messages
            finally:
                await pool.close()

        outcome, messages = asyncio.run(publish_and_observe())
        assert outcome.completed is True
        observed_message_ids: dict[str, str | None] = {}
        for message in messages:
            document = json.loads(message.data.decode("utf-8"))
            event_id = str(document["event_id"])
            if event_id in expected_replay_ids:
                observed_message_ids[event_id] = message.headers.get("Nats-Msg-Id")
        assert set(observed_message_ids) == expected_replay_ids
        assert all(
            observed_message_ids[event_id] == event_id
            for event_id in expected_replay_ids
        )
    finally:
        manager.stop_one("west")
''',
        "external replay identity test",
    )

    text = replace_once(
        text,
        '''def test_f2p_retention_policy_covers_recovery_horizon(engine: ContinuityEngine) -> None:
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
''',
        '''def test_f2p_retention_policy_covers_recovery_horizon(engine: ContinuityEngine) -> None:
    """JetStream ages and durable journal cleanup both cover the full recovery horizon."""
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

    complete_archive(engine, "east")
    for consumer in engine.store.required_consumers():
        set_checkpoint(engine, consumer, "east", effect=6000)

    at = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
    within_horizon = "evt-east-g01-000100"
    beyond_horizon = "evt-east-g01-000101"
    engine.store.execute(
        "UPDATE event_journal SET retention_hold=0,accepted_at=? WHERE event_id=?",
        ((at - timedelta(hours=24)).isoformat(), within_horizon),
    )
    engine.store.execute(
        "UPDATE event_journal SET retention_hold=0,accepted_at=? WHERE event_id=?",
        ((at - timedelta(hours=72)).isoformat(), beyond_horizon),
    )

    decision = engine.compute_retention_decision(
        region="east",
        generation=1,
        at=at,
        limit=1000,
    )
    candidates = set(decision.eligible_event_ids)
    assert within_horizon not in candidates
    assert beyond_horizon in candidates
''',
        "journal recovery horizon test",
    )
    path.write_text(text, encoding="utf-8")


def patch_report_test() -> None:
    path = TASK / "tests/test_contract_coverage.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''    health = json.loads(health_path.read_text(encoding="utf-8"))
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    config = json.loads(
''',
        '''    health = json.loads(health_path.read_text(encoding="utf-8"))
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    for report in (health, reconciliation):
        generated_at = report.get("generated_at")
        assert isinstance(generated_at, str) and generated_at
        parsed_generated_at = datetime.fromisoformat(
            generated_at.replace("Z", "+00:00")
        )
        assert parsed_generated_at.tzinfo is not None
    config = json.loads(
''',
        "generated_at report assertion",
    )
    path.write_text(text, encoding="utf-8")


def patch_reference_engine() -> None:
    path = TASK / "solution/files/engine.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "            minimum_age_seconds=policy.journal_min_age_seconds,\n",
        '''            minimum_age_seconds=max(
                policy.journal_min_age_seconds,
                policy.required_horizon_seconds,
            ),
''',
        "reference journal horizon",
    )
    path.write_text(text, encoding="utf-8")


def patch_test_map() -> None:
    path = Path(".terminus/designs/jetstream-regional-stream-continuity-test-map.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["requirements"]["REQ-19"] = (
        "Configured raw retention and effective durable edge-journal cleanup age cover "
        "the declared maximum disconnect, replay and safety recovery horizon."
    )
    data["requirements"]["REQ-24"] = (
        "The submitted repair materializes health.json and reconciliation.json under "
        "/app/continuity/out/ with the documented stable report interface, including "
        "parseable generated_at timestamps, without rewriting captured incident state."
    )
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def validate_shape() -> None:
    total = f2p = p2p = 0
    for path in (TASK / "tests/test_continuity.py", TASK / "tests/test_contract_coverage.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                total += 1
                if node.name.startswith("test_f2p_"):
                    f2p += 1
                elif node.name.startswith("test_p2p_"):
                    p2p += 1
    if (total, f2p, p2p) != (40, 30, 10):
        raise SystemExit(f"unexpected test matrix {(total, f2p, p2p)}")
    data = json.loads(Path(".terminus/designs/jetstream-regional-stream-continuity-test-map.json").read_text(encoding="utf-8"))
    mapped = data["tests"]
    if len(mapped) != 40:
        raise SystemExit(f"unexpected mapped tests {len(mapped)}")
    if sum(row[1] == "F2P" for row in mapped) != 30:
        raise SystemExit("test map no longer has 30 F2P")
    if sum(row[1] == "P2P" for row in mapped) != 10:
        raise SystemExit("test map no longer has 10 P2P")


def main() -> None:
    patch_tests()
    patch_report_test()
    patch_reference_engine()
    patch_test_map()
    validate_shape()


if __name__ == "__main__":
    main()
