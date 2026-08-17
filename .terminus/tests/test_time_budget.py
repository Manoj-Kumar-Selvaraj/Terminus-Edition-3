from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from execution.time_budget import BudgetPolicy, TaskTimeBudget


UTC = timezone.utc


def test_budget_accumulates_stage_and_run_time(tmp_path):
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
    assert snapshot["consumed_seconds"] == 1380
    assert snapshot["stage_totals_seconds"] == {"ORACLE": 300, "Q1": 1080}
    assert snapshot["category_totals_seconds"]["QUALITY_REVIEW"] == 1080
    assert snapshot["recommended_next_stage_seconds"] == (14400 - 1380) // 3


def test_budget_modes_and_hard_limit_request(tmp_path):
    manager = TaskTimeBudget(
        tmp_path,
        "task-b",
        policy=BudgetPolicy(target_seconds=1000, hard_seconds=1200),
    )
    manager.record_run("A", 600)
    assert manager.snapshot()["mode"] == "BUDGET_AWARE"

    manager.record_run("B", 150)
    assert manager.snapshot()["mode"] == "CONSERVE"

    manager.record_run("C", 150)
    assert manager.snapshot()["mode"] == "CRITICAL"

    manager.record_run("D", 300)
    snapshot = manager.snapshot()
    assert snapshot["mode"] == "HARD_LIMIT"
    assert snapshot["request_time_extension"] is True


def test_human_extension_reopens_budget(tmp_path):
    manager = TaskTimeBudget(
        tmp_path,
        "task-c",
        policy=BudgetPolicy(target_seconds=1000, hard_seconds=1200),
    )
    manager.record_run("Q4", 1200, category="QUALITY_REVIEW")
    assert manager.snapshot()["request_time_extension"] is True

    extension = manager.grant_extension(
        60,
        approved_by="human-owner",
        reason="finish remaining mandatory gates",
    )
    assert extension["seconds"] == 3600
    snapshot = manager.snapshot()
    assert snapshot["request_time_extension"] is False
    assert snapshot["target_seconds"] == 4600
    assert snapshot["hard_limit_seconds"] == 4800


def test_workflow_projection_overrides_next_at_hard_limit(tmp_path):
    manager = TaskTimeBudget(
        tmp_path,
        "task-d",
        policy=BudgetPolicy(target_seconds=100, hard_seconds=120),
    )
    manager.record_run("Q2", 120)
    workflow = {
        "nodes": [
            {"node_id": "Q4", "node_kind": "STAGE", "status": "MISSING"},
            {"node_id": "Q6", "node_kind": "STAGE", "status": "MISSING"},
        ],
        "next": {"action": "INVOKE_STAGE", "stage_id": "Q4"},
    }
    projected = manager.project_workflow(workflow)
    assert projected["next"]["action"] == "REQUEST_TIME_EXTENSION"
    assert projected["time_budget"]["remaining_mandatory_stages"] == 2


def test_extension_requires_explicit_human_identity(tmp_path):
    manager = TaskTimeBudget(tmp_path, "task-e")
    with pytest.raises(ValueError, match="approved_by"):
        manager.grant_extension(60, approved_by="")
