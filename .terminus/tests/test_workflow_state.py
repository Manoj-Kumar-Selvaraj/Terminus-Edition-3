from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.invocation import StageInvocationBuilder  # noqa: E402
from execution.ledger import ExecutionLedger  # noqa: E402
from execution.record import ExecutionRecordBuilder  # noqa: E402
from execution.state import WorkflowStateResolver  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402


def _run(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _temp_control_repo(tmp_path: Path) -> tuple[Path, str]:
    """Use a complete control-plane clone so canonical replay is test-realistic."""
    root = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", "--quiet", "--shared", str(ROOT), str(root)],
        check=True,
    )
    _run(root, "config", "user.email", "terminus-tests@example.invalid")
    _run(root, "config", "user.name", "Terminus Tests")
    return root, _run(root, "rev-parse", "HEAD")


def _new_commit(root: Path, name: str) -> str:
    (root / name).write_text(name + "\n", encoding="utf-8")
    _run(root, "add", name)
    _run(root, "commit", "-m", name)
    return _run(root, "rev-parse", "HEAD")


def _review_pass() -> dict[str, object]:
    return {
        "review_id": "fixture-review",
        "verdict": "PASS",
        "confidence": "MEDIUM",
        "evidence_status": "SUFFICIENT",
        "missing_evidence": [],
    }


def _valid_outputs(
    resolver: WorkflowStateResolver, stage_id: str
) -> dict[str, object]:
    stage = resolver.policy.stages[stage_id]
    outputs: dict[str, object] = {
        name: "ok" for name in stage["output_contract"]["required_fields"]
    }
    if stage_id == "RULE_RESOLUTION":
        outputs["KNOWN_POLICY_CONFLICTS"] = []
    elif stage_id == "SPEC_ALIGNMENT":
        outputs.update(Q1_STATUS="NO_GAP", Q2_STATUS="COVERED", Q3_STATUS="CLEAR")
    elif stage_id == "RUNTIME_AUTHENTICITY":
        outputs["RUNTIME_AUTHENTICITY_STATUS"] = "PASS"
    elif stage_id == "DETERMINISTIC_VALIDATION":
        outputs.update(
            ORACLE_REWARD=1,
            NOP_REWARD=0,
            F2P_EMPIRICAL_MATRIX=[{"case": "f2p", "pass": True}],
            P2P_EMPIRICAL_MATRIX=[{"case": "p2p", "pass": True}],
        )
    elif stage_id == "QUALITY_INTERLOCK":
        outputs.update(
            Q4_RESULT=_review_pass(),
            Q6_RESULT=_review_pass(),
            EVIDENCE_SUFFICIENCY="SUFFICIENT",
        )
    elif stage_id == "PRE_LLMAJ":
        outputs.update({f"STAGE_{letter}": "PASS" for letter in "ABCDEF"})
    elif stage_id == "MODEL_DIAGNOSTIC_GPT":
        outputs.update(
            PERSPECTIVE="GPT_PERSPECTIVE",
            EXECUTION="EXECUTED",
            DIAGNOSTIC_SUMMARY="diagnostic",
            PREDICTED_OFFICIAL_SIGNAL="non-authoritative",
        )
    elif stage_id == "MODEL_DIAGNOSTIC_CLAUDE":
        outputs.update(
            PERSPECTIVE="CLAUDE_PERSPECTIVE",
            EXECUTION="EXECUTED",
            DIAGNOSTIC_SUMMARY="diagnostic",
            PREDICTED_OFFICIAL_SIGNAL="non-authoritative",
        )
    elif stage_id == "MODEL_DIAGNOSTIC_AGGREGATE":
        outputs.update(
            GPT_PERSPECTIVE_RESULT={"EXECUTION": "EXECUTED"},
            CLAUDE_PERSPECTIVE_RESULT={"EXECUTION": "EXECUTED"},
            ISOLATION_CHECK="PASS",
            COMPARATIVE_DIAGNOSTIC="complete",
        )
    elif stage_id == "HARBOR_LLMAJ":
        outputs.update(
            HARBOR_RUN_ID="harbor-run-1",
            HARBOR_RESULT="PASS",
            HARBOR_EVIDENCE={"artifact": "harbor-run-1"},
        )
    elif stage_id == "OFFICIAL_MODEL_TRIALS":
        outputs.update(
            GPT_5_5_TRIALS=[
                {"trial": i, "run_id": f"gpt-run-{i}"} for i in range(5)
            ],
            CLAUDE_OPUS_4_8_TRIALS=[
                {"trial": i, "run_id": f"claude-run-{i}"} for i in range(5)
            ],
            COMBINED_SUCCESS_RATE=0.5,
            PER_TEST_SOLVABILITY={"test_f2p_example": 1},
        )
    elif stage_id == "TRIAL_ANALYSIS":
        outputs.update(
            FAILURE_CLASSIFICATION={},
            ZERO_OF_TEN_DISPOSITION="NONE",
            REMEDIATION_OWNER="NONE",
        )
    elif stage_id == "DIFFICULTY_ASSESSMENT":
        outputs.update(
            EMPIRICAL_TIER="advanced",
            DECLARED_TIER="advanced",
            COMBINED_SUCCESS_RATE=0.5,
            PER_TEST_SOLVABILITY={"test_f2p_example": 1},
            ZERO_OF_TEN_TESTS=[],
            TRAJECTORY_ANALYSIS_RESULT={
                "status": "COMPLETE",
                "record_id": "trajectory-result",
            },
        )
    elif stage_id == "FINAL_REVIEW":
        outputs.update(
            FINAL_COMPLIANCE=_review_pass(),
            FINAL_HUMAN_QUALITY=_review_pass(),
            FINAL_PACKAGE_EVIDENCE={"manifest": "ok"},
        )
    elif stage_id == "SUBMISSION_READY":
        outputs.update(
            READINESS_STATUS="SUBMISSION_READY",
            GATE_EVIDENCE={"all": "current"},
        )
    return outputs


def _external_ref(identity: str) -> dict[str, str]:
    digest = "sha256:" + hashlib.sha256(identity.encode()).hexdigest()
    return {
        "kind": "EXTERNAL",
        "ref": f"external:test:{identity}#{digest}",
        "content_hash": digest,
    }


def _record(
    resolver: WorkflowStateResolver,
    stage_id: str,
    task_id: str,
    commit: str,
    *,
    output_commit: str | None = None,
    control_commit: str | None = None,
    attempt: int = 1,
    status: str | None = None,
    evidence_refs: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build every workflow-state fixture through canonical invocation/record APIs."""
    stage = resolver.policy.stages[stage_id]
    outcome = resolver.outcomes["stages"][stage_id]
    if status is None:
        status = outcome["advance_statuses"][0]
    output_commit = output_commit or commit
    control_commit = control_commit or commit
    role_id = resolver.execution_authority.primary_role_for_stage(stage_id)
    required = {
        str(field): {"fixture": str(field)}
        for field in stage["input_contract"]["required_fields"]
    }
    optional_fields = list(stage["input_contract"].get("optional_fields", []))
    inputs: dict[str, object] = dict(required)
    if optional_fields:
        inputs[str(optional_fields[0])] = {"fixture_attempt": attempt}
    invocation = StageInvocationBuilder(resolver.root, resolver.policy).build(
        InvocationContext(
            stage_id=stage_id,
            role_id=role_id,
            task_id=task_id,
            task_commit=commit,
            control_plane_commit=control_commit,
        ),
        inputs,
    )
    result: dict[str, object] = {
        "schema_version": "1.0",
        "invocation_id": invocation["invocation_id"],
        "output_task_commit": output_commit,
        "status": status,
        "outputs": _valid_outputs(resolver, stage_id),
        "evidence_refs": evidence_refs or [],
    }
    disposition = resolver.record_builder._disposition(outcome, status)
    if disposition == "BLOCK":
        result["blocking_reason"] = "test block"
    elif disposition == "ROUTE":
        semantics = outcome["route_statuses"][status]
        result["route_key"] = (
            semantics.get("default_route_key")
            or semantics["allowed_route_keys"][0]
        )
    return ExecutionRecordBuilder(resolver.root, resolver.policy).build(
        invocation, result
    )


def _append_through_freeze_predecessor(
    root: Path,
    resolver: WorkflowStateResolver,
    task_id: str,
    commit: str,
    *,
    work_package_evidence: list[dict[str, object]] | None = None,
) -> ExecutionLedger:
    ledger = ExecutionLedger(root, task_id)
    for descriptor in resolver.chain:
        if descriptor["node_kind"] == "STATE":
            break
        stage_id = descriptor["node_id"]
        refs = (
            work_package_evidence
            if stage_id == "WORK_PACKAGE_RESEARCH"
            else None
        )
        ledger.append(
            _record(
                resolver,
                stage_id,
                task_id,
                commit,
                evidence_refs=refs,
            )
        )
    return ledger


def test_empty_ledger_starts_at_rule_resolution(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    state = WorkflowStateResolver(root).resolve(
        task_id="task-empty",
        task_commit=commit,
        control_plane_commit=commit,
    )
    assert state["summary"]["CURRENT"] == 0
    assert state["lineage"]["status"] == "UNINITIALIZED"
    assert state["next"]["stage_id"] == "RULE_RESOLUTION"


def test_first_record_bootstraps_task_lineage(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    ledger = ExecutionLedger(root, "task-first")
    ledger.append(_record(resolver, "RULE_RESOLUTION", "task-first", commit))
    state = resolver.resolve(
        task_id="task-first", task_commit=commit, control_plane_commit=commit
    )
    assert state["nodes"][0]["status"] == "CURRENT"
    assert state["lineage"]["bootstrap_task_commit"] == commit
    assert state["lineage"]["recorded_task_commit"] == commit
    assert state["lineage"]["status"] == "CURRENT"


def test_task_drift_blocks_unattributed_change(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    ledger = ExecutionLedger(root, "task-drift")
    ledger.append(_record(resolver, "RULE_RESOLUTION", "task-drift", commit))
    changed = _new_commit(root, "unattributed.txt")
    state = resolver.resolve(
        task_id="task-drift", task_commit=changed, control_plane_commit=commit
    )
    assert state["lineage"]["status"] == "UNATTRIBUTED_CHANGE"
    assert state["next"]["action"] == "BLOCKED"
    assert "unattributed" in state["next"]["blocking_reason"]


def test_downstream_record_stales_when_predecessor_is_newer(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    ledger = ExecutionLedger(root, "task-sequence")
    ledger.append(
        _record(resolver, "RULE_RESOLUTION", "task-sequence", commit, attempt=1)
    )
    ledger.append(
        _record(
            resolver,
            "WORK_PACKAGE_RESEARCH",
            "task-sequence",
            commit,
            attempt=1,
        )
    )
    ledger.append(
        _record(resolver, "RULE_RESOLUTION", "task-sequence", commit, attempt=2)
    )
    state = resolver.resolve(
        task_id="task-sequence", task_commit=commit, control_plane_commit=commit
    )
    by_id = {node["node_id"]: node for node in state["nodes"]}
    assert by_id["RULE_RESOLUTION"]["status"] == "CURRENT"
    assert by_id["WORK_PACKAGE_RESEARCH"]["status"] == "STALE"
    assert state["next"]["stage_id"] == "WORK_PACKAGE_RESEARCH"


def test_freeze_is_derived_only_when_entry_requirements_pass(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    _append_through_freeze_predecessor(root, resolver, "task-freeze", commit)
    state = resolver.resolve(
        task_id="task-freeze", task_commit=commit, control_plane_commit=commit
    )
    freeze = next(
        node for node in state["nodes"] if node["node_id"] == "FROZEN_CANDIDATE"
    )
    assert freeze["status"] == "CURRENT"
    assert all(item.endswith("PASS") for item in freeze["entry_requirements"])
    assert state["next"]["stage_id"] == "QUALITY_INTERLOCK"


def test_stale_work_package_evidence_invalidates_downstream(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    ref = _external_ref("domain-research")
    _append_through_freeze_predecessor(
        root,
        resolver,
        "task-freshness",
        commit,
        work_package_evidence=[ref],
    )
    overlay = {
        "schema_version": "1.0",
        "bindings": {
            ref["ref"]: {
                "status": "STALE",
                "content_hash": "sha256:" + "2" * 64,
                "reason": "newer external research is available",
            }
        },
    }
    state = resolver.resolve(
        task_id="task-freshness",
        task_commit=commit,
        control_plane_commit=commit,
        freshness_overlay=overlay,
    )
    by_id = {node["node_id"]: node for node in state["nodes"]}
    assert by_id["WORK_PACKAGE_RESEARCH"]["status"] == "STALE"
    assert by_id["SYSTEM_ARCHITECTURE"]["status"] == "STALE"
    assert state["next"]["stage_id"] == "WORK_PACKAGE_RESEARCH"


def test_materialized_state_is_derived_and_gitignored(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    state = resolver.resolve(
        task_id="task-materialized",
        task_commit=commit,
        control_plane_commit=commit,
    )
    path = resolver.materialize(state)
    assert (
        path
        == root / ".terminus" / "workflows" / "task-materialized" / "state.json"
    )
    materialized = json.loads(path.read_text(encoding="utf-8"))
    assert materialized["state_snapshot_id"] == state["state_snapshot_id"]
