from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from execution.time_budget import BudgetPolicy, TaskTimeBudget


UTC = timezone.utc


def test_time_telemetry_accumulates_without_stage_envelope(tmp_path):
    manager = TaskTimeBudget(tmp_path, "task-a")
    start = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)
    manager.begin("Q1", started_at=start)
    event = manager.finish(
        finished_at=start + timedelta(minutes=20),
        paused_seconds=120,
        category="QUALITY_REVIEW",
    )
    assert event["wall_seconds"] == 1200
    assert event["counted_seconds"] == 1080

    manager.record_run(
        "ORACLE",
        300,
        category="DETERMINISTIC_VALIDATION",
        finished_at=start + timedelta(minutes=30),
    )
    snapshot = manager.snapshot(remaining_mandatory_stages=3)
    assert snapshot["schema_version"] == "1.1"
    assert snapshot["enforcement"] == "ADVISORY_ONLY"
    assert snapshot["guidance_seconds"] == 7 * 60 * 60
    assert snapshot["consumed_seconds"] == 1380
    assert snapshot["stage_totals_seconds"] == {"ORACLE": 300, "Q1": 1080}
    assert snapshot["category_totals_seconds"]["QUALITY_REVIEW"] == 1080
    assert snapshot["recommended_next_stage_seconds"] is None
    assert snapshot["hard_limit_seconds"] is None
    assert snapshot["request_time_extension"] is False


def test_exceeding_guidance_never_requests_extension(tmp_path):
    manager = TaskTimeBudget(
        tmp_path,
        "task-b",
        policy=BudgetPolicy(target_seconds=1000, hard_seconds=1200),
    )
    manager.record_run("A", 1500)
    snapshot = manager.snapshot()
    assert snapshot["mode"] == "ADVISORY_OVER_GUIDANCE"
    assert snapshot["guidance_exceeded"] is True
    assert snapshot["hard_limit_seconds"] is None
    assert snapshot["hard_remaining_seconds"] is None
    assert snapshot["request_time_extension"] is False


def test_workflow_projection_never_overrides_canonical_next(tmp_path):
    manager = TaskTimeBudget(
        tmp_path,
        "task-c",
        policy=BudgetPolicy(target_seconds=100, hard_seconds=120),
    )
    manager.record_run("Q2", 500)
    workflow = {
        "nodes": [
            {"node_id": "Q4", "node_kind": "STAGE", "status": "MISSING"},
            {"node_id": "Q6", "node_kind": "STAGE", "status": "MISSING"},
        ],
        "next": {"action": "INVOKE_STAGE", "stage_id": "Q4"},
    }
    projected = manager.project_workflow(workflow)
    assert projected["next"] == workflow["next"]
    assert projected["time_budget"]["remaining_mandatory_stages"] == 2
    assert projected["time_budget"]["guidance_exceeded"] is True
    assert projected["time_budget"]["request_time_extension"] is False


def test_legacy_extension_metadata_does_not_change_guidance(tmp_path):
    manager = TaskTimeBudget(tmp_path, "task-d")
    baseline = manager.snapshot()["guidance_seconds"]
    extension = manager.grant_extension(
        60,
        approved_by="human-owner",
        reason="legacy compatibility",
    )
    assert extension["advisory_only"] is True
    snapshot = manager.snapshot()
    assert snapshot["guidance_seconds"] == baseline
    assert snapshot["target_seconds"] == baseline
    assert snapshot["extension_seconds"] == 3600
    assert snapshot["request_time_extension"] is False


def test_extension_requires_explicit_human_identity_for_legacy_metadata(tmp_path):
    manager = TaskTimeBudget(tmp_path, "task-e")
    with pytest.raises(ValueError, match="approved_by"):
        manager.grant_extension(60, approved_by="")
