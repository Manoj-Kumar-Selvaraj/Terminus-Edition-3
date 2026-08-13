from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.ledger import ExecutionLedger  # noqa: E402
from execution.record import ExecutionRecordBuilder  # noqa: E402
from execution.state import WorkflowStateResolver  # noqa: E402


def _run(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _temp_control_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    (root / ".terminus").mkdir(parents=True)
    shutil.copytree(ROOT / ".terminus" / "agents", root / ".terminus" / "agents")
    _run(root, "init")
    _run(root, "config", "user.email", "terminus-tests@example.invalid")
    _run(root, "config", "user.name", "Terminus Tests")
    _run(root, "add", ".")
    _run(root, "commit", "-m", "control snapshot")
    return root, _run(root, "rev-parse", "HEAD")


def _new_commit(root: Path, name: str) -> str:
    (root / name).write_text(name + "\n", encoding="utf-8")
    _run(root, "add", name)
    _run(root, "commit", "-m", name)
    return _run(root, "rev-parse", "HEAD")


def _invocation_id(label: str) -> str:
    return "inv_" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _review_pass() -> dict[str, object]:
    return {"verdict": "PASS", "confidence": "MEDIUM", "evidence_status": "SUFFICIENT", "missing_evidence": []}


def _valid_outputs(resolver: WorkflowStateResolver, stage_id: str) -> dict[str, object]:
    stage = resolver.policy.stages[stage_id]
    outputs: dict[str, object] = {name: "ok" for name in stage["output_contract"]["required_fields"]}
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
        outputs.update(Q4_RESULT=_review_pass(), Q6_RESULT=_review_pass(), EVIDENCE_SUFFICIENCY="SUFFICIENT")
    elif stage_id == "PRE_LLMAJ":
        outputs.update({f"STAGE_{letter}": "PASS" for letter in "ABCDEF"})
    elif stage_id == "OFFICIAL_MODEL_TRIALS":
        outputs.update(
            GPT_5_5_TRIALS=[{"trial": i} for i in range(5)],
            CLAUDE_OPUS_4_8_TRIALS=[{"trial": i} for i in range(5)],
            PER_TEST_SOLVABILITY={"test_f2p_example": 1},
        )
    elif stage_id == "FINAL_REVIEW":
        outputs.update(FINAL_COMPLIANCE=_review_pass(), FINAL_HUMAN_QUALITY=_review_pass(), FINAL_PACKAGE_EVIDENCE={"manifest": "ok"})
    elif stage_id == "SUBMISSION_READY":
        outputs.update(READINESS_STATUS="SUBMISSION_READY", GATE_EVIDENCE={"all": "current"})
    return outputs


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
    stage = resolver.policy.stages[stage_id]
    outcome = resolver.outcomes["stages"][stage_id]
    if status is None:
        status = outcome["advance_statuses"][0]
    disposition = resolver.record_builder._disposition(outcome, status)
    outputs = _valid_outputs(resolver, stage_id)
    output_commit = output_commit or commit
    control_commit = control_commit or commit
    success_target = str(stage["success_transition"])
    if disposition == "ADVANCE":
        target_kind = "END" if success_target == "END" else "STATE" if success_target in resolver.completion["state_contracts"] else "STAGE"
        transition: dict[str, object] = {
            "action": "ADVANCE", "target": success_target, "target_kind": target_kind,
            "requires_state_validation": target_kind == "STATE",
        }
    elif disposition == "RETRY":
        transition = {"action": "RETRY", "target": stage_id, "target_kind": "STAGE", "requires_state_validation": False}
    elif disposition == "BLOCK":
        transition = {"action": "BLOCK", "target": None, "target_kind": "NONE", "requires_state_validation": False}
    else:
        semantics = outcome["route_statuses"][status]
        route_key = semantics.get("default_route_key") or semantics["allowed_route_keys"][0]
        transition = {
            "action": "ROUTE", "target": None, "target_kind": "ROUTE",
            "route_key": route_key, "route_instruction": stage["failure_routes"][route_key],
            "requires_state_validation": False,
        }
    refs = evidence_refs or []
    value: dict[str, object] = {
        "schema_version": "1.0",
        "invocation_id": _invocation_id(f"{stage_id}:{attempt}:{commit}:{output_commit}"),
        "stage_id": stage_id,
        "role_id": resolver.execution_authority.primary_role_for_stage(stage_id),
        "authority": {"task_id": task_id, "task_commit": commit, "control_plane_commit": control_commit, "policy_versions": {}},
        "task_lineage": {"input_task_commit": commit, "output_task_commit": output_commit, "task_changed": output_commit != commit},
        "status": status,
        "disposition": disposition,
        "outputs": outputs,
        "evidence_refs": refs,
        "transition": transition,
        "validation": {
            "invocation_identity_valid": True,
            "status_legal": True,
            "output_keys_valid": True,
            "required_outputs_satisfied": status in outcome["full_output_statuses"],
            "task_lineage_valid": True,
            "task_commit_change_authorized": True,
            "acceptance_predicates_satisfied": True,
            "evidence_refs_count": len(refs),
        },
    }
    if disposition == "ROUTE":
        value["route_key"] = transition["route_key"]
    if disposition == "BLOCK":
        value["blocking_reason"] = "test block"
    value["record_id"] = ExecutionRecordBuilder._record_id(value)
    return value


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
        refs = work_package_evidence if stage_id == "WORK_PACKAGE_RESEARCH" else None
        ledger.append(_record(resolver, stage_id, task_id, commit, evidence_refs=refs))
    return ledger


def test_empty_ledger_starts_at_rule_resolution(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    state = WorkflowStateResolver(root).resolve(task_id="task-empty", task_commit=commit, control_plane_commit=commit)
    assert state["summary"]["CURRENT"] == 0
    assert state["lineage"]["status"] == "UNINITIALIZED"
    assert state["next"]["stage_id"] == "RULE_RESOLUTION"


def test_complete_creation_chain_materializes_frozen_candidate(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    _append_through_freeze_predecessor(root, resolver, "task-freeze", commit)
    state = resolver.resolve(task_id="task-freeze", task_commit=commit, control_plane_commit=commit)
    frozen = next(node for node in state["nodes"] if node["node_id"] == "FROZEN_CANDIDATE")
    assert frozen["status"] == "CURRENT"
    assert all(item.endswith("PASS") for item in frozen["entry_requirements"])
    assert state["lineage"]["status"] == "CURRENT"
    assert state["next"]["stage_id"] == "QUALITY_INTERLOCK"


def test_recorded_producer_commit_lineage_remains_current(tmp_path: Path) -> None:
    root, commit_a = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    ledger = ExecutionLedger(root, "task-lineage")
    ledger.append(_record(resolver, "RULE_RESOLUTION", "task-lineage", commit_a))
    commit_b = _new_commit(root, "task-change.txt")
    ledger.append(
        _record(
            resolver, "WORK_PACKAGE_RESEARCH", "task-lineage", commit_a,
            output_commit=commit_b, control_commit=commit_a,
        )
    )
    state = resolver.resolve(task_id="task-lineage", task_commit=commit_b, control_plane_commit=commit_a)
    rule = state["nodes"][0]
    work = state["nodes"][1]
    assert rule["status"] == "CURRENT"
    assert work["status"] == "CURRENT"
    assert work["input_task_commit"] == commit_a
    assert work["output_task_commit"] == commit_b
    assert state["lineage"]["status"] == "CURRENT"
    assert state["next"]["stage_id"] == "SYSTEM_ARCHITECTURE"


def test_unattributed_task_change_blocks_next_stage(tmp_path: Path) -> None:
    root, commit_a = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    ExecutionLedger(root, "task-unattributed").append(
        _record(resolver, "RULE_RESOLUTION", "task-unattributed", commit_a)
    )
    commit_b = _new_commit(root, "unattributed.txt")
    state = resolver.resolve(task_id="task-unattributed", task_commit=commit_b, control_plane_commit=commit_a)
    work = next(node for node in state["nodes"] if node["node_id"] == "WORK_PACKAGE_RESEARCH")
    assert work["status"] == "BLOCKED"
    assert "unattributed" in work["reason"]
    assert state["lineage"]["status"] == "UNATTRIBUTED_CHANGE"
    assert state["next"]["action"] == "BLOCKED"


def test_broken_stage_input_lineage_is_stale(tmp_path: Path) -> None:
    root, commit_a = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    ledger = ExecutionLedger(root, "task-broken-lineage")
    ledger.append(_record(resolver, "RULE_RESOLUTION", "task-broken-lineage", commit_a))
    commit_b = _new_commit(root, "skip.txt")
    ledger.append(
        _record(
            resolver, "WORK_PACKAGE_RESEARCH", "task-broken-lineage", commit_b,
            control_commit=commit_a,
        )
    )
    state = resolver.resolve(task_id="task-broken-lineage", task_commit=commit_b, control_plane_commit=commit_a)
    work = state["nodes"][1]
    assert work["status"] == "STALE"
    assert "does not match the latest current predecessor" in work["reason"]
    assert state["next"]["stage_id"] == "WORK_PACKAGE_RESEARCH"


def test_later_retry_supersedes_earlier_format_pass(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    ledger = _append_through_freeze_predecessor(root, resolver, "task-retry", commit)
    ledger.append(_record(resolver, "FORMAT_GATE", "task-retry", commit, attempt=2, status="FIXED"))
    state = resolver.resolve(task_id="task-retry", task_commit=commit, control_plane_commit=commit)
    format_node = next(node for node in state["nodes"] if node["node_id"] == "FORMAT_GATE")
    assert format_node["status"] == "BLOCKED"
    assert state["next"]["action"] == "RETRY_STAGE"
    assembly = next(node for node in state["nodes"] if node["node_id"] == "ASSEMBLY")
    assert assembly["status"] == "STALE"


def test_explicit_evidence_freshness_invalidates_citing_stage(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    _append_through_freeze_predecessor(
        root, resolver, "task-evidence", commit,
        work_package_evidence=[{"kind": "EXTERNAL", "ref": "external:work-package", "content_hash": "sha256:" + "a" * 64}],
    )
    stale = resolver.resolve(
        task_id="task-evidence", task_commit=commit, control_plane_commit=commit,
        freshness_overlay={"schema_version": "1.0", "bindings": {"external:work-package": {"status": "STALE", "reason": "superseded"}}},
    )
    work = next(node for node in stale["nodes"] if node["node_id"] == "WORK_PACKAGE_RESEARCH")
    assert work["status"] == "STALE"
    assert stale["next"]["stage_id"] == "WORK_PACKAGE_RESEARCH"


def test_ledger_detects_record_tampering(tmp_path: Path) -> None:
    ledger = ExecutionLedger(tmp_path, "task-ledger")
    record = {
        "record_id": "rec_" + "1" * 64,
        "invocation_id": "inv_" + "2" * 64,
        "stage_id": "RULE_RESOLUTION",
        "authority": {"task_id": "task-ledger", "task_commit": "a" * 40, "control_plane_commit": "b" * 40},
        "task_lineage": {"input_task_commit": "a" * 40, "output_task_commit": "a" * 40, "task_changed": False},
    }
    ledger.append(record)
    path = ledger.record_path(record["invocation_id"])
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="content hash mismatch"):
        ledger.load(validate_record_files=True)


def test_state_snapshot_is_deterministic_and_materializable(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    first = resolver.resolve(task_id="task-materialized", task_commit=commit, control_plane_commit=commit)
    second = resolver.resolve(task_id="task-materialized", task_commit=commit, control_plane_commit=commit)
    assert first == second
    path = resolver.materialize(first)
    assert json.loads(path.read_text(encoding="utf-8")) == first
