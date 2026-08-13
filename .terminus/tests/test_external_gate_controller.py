from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / ".terminus" / "tests"
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.external_gate import project_external_state, validate_external_result  # noqa: E402
from execution.ledger import ExecutionLedger  # noqa: E402
from execution.state import WorkflowStateResolver  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from execution.invocation import StageInvocationBuilder  # noqa: E402
from test_workflow_state import _record, _temp_control_repo  # noqa: E402


def _append_until(
    root: Path,
    resolver: WorkflowStateResolver,
    task_id: str,
    commit: str,
    stop_before: str,
) -> ExecutionLedger:
    ledger = ExecutionLedger(root, task_id)
    for descriptor in resolver.chain:
        if descriptor["node_kind"] != "STAGE":
            continue
        stage_id = descriptor["node_id"]
        if stage_id == stop_before:
            break
        ledger.append(_record(resolver, stage_id, task_id, commit))
    return ledger


def test_missing_harbor_projects_dispatch_external_gate(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    _append_until(root, resolver, "task-harbor-dispatch", commit, "HARBOR_LLMAJ")
    raw = resolver.resolve(
        task_id="task-harbor-dispatch",
        task_commit=commit,
        control_plane_commit=commit,
    )
    assert raw["next"]["action"] == "INVOKE_STAGE"
    assert raw["next"]["stage_id"] == "HARBOR_LLMAJ"
    projected = project_external_state(root, resolver, raw)
    assert projected["next"]["action"] == "DISPATCH_EXTERNAL_GATE"
    assert projected["next"]["stage_id"] == "HARBOR_LLMAJ"
    assert projected["next"]["external_gate"] is True
    assert projected["state_snapshot_id"] != raw["state_snapshot_id"]


def test_dispatched_harbor_projects_await_with_run_id(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    ledger = _append_until(root, resolver, "task-harbor-await", commit, "HARBOR_LLMAJ")
    ledger.append(
        _record(
            resolver,
            "HARBOR_LLMAJ",
            "task-harbor-await",
            commit,
            status="DISPATCHED",
            outputs_override={"EXTERNAL_RUN_ID": "harbor-run-42"},
        )
    )
    raw = resolver.resolve(
        task_id="task-harbor-await",
        task_commit=commit,
        control_plane_commit=commit,
    )
    assert raw["next"]["action"] == "RETRY_STAGE"
    projected = project_external_state(root, resolver, raw)
    assert projected["next"]["action"] == "AWAIT_EXTERNAL_GATE"
    assert projected["next"]["external_run_id"] == "harbor-run-42"


def test_external_result_requires_run_identity_before_recording(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    stage = resolver.policy.stages["OFFICIAL_MODEL_TRIALS"]
    invocation = StageInvocationBuilder(root, resolver.policy).build(
        InvocationContext(
            stage_id="OFFICIAL_MODEL_TRIALS",
            role_id="OFFICIAL_MODEL_EVALUATION_GATE",
            task_id="task-official-run-id",
            task_commit=commit,
            control_plane_commit=commit,
        ),
        {str(field): "test" for field in stage["input_contract"]["required_fields"]},
    )
    result = {
        "schema_version": "1.0",
        "invocation_id": invocation["invocation_id"],
        "output_task_commit": commit,
        "status": "DISPATCHED",
        "outputs": {},
        "evidence_refs": [],
    }
    with pytest.raises(ValueError, match="requires a non-empty immutable run ID"):
        validate_external_result(resolver.policy, invocation, result)
    result["outputs"] = {"EXTERNAL_RUN_ID": "official-run-1"}
    validate_external_result(resolver.policy, invocation, result)
