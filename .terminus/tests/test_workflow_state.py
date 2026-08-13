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
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
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


def _invocation_id(label: str) -> str:
    return "inv_" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _record(
    resolver: WorkflowStateResolver,
    stage_id: str,
    task_id: str,
    commit: str,
    *,
    attempt: int = 1,
    status: str | None = None,
    evidence_refs: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    stage = resolver.policy.stages[stage_id]
    outcome = resolver.outcomes["stages"][stage_id]
    if status is None:
        status = outcome["advance_statuses"][0]
    disposition = resolver.record_builder._disposition(outcome, status)
    output_contract = stage["output_contract"]
    outputs = {name: "ok" for name in output_contract["required_fields"]}
    if stage_id == "RULE_RESOLUTION":
        outputs["KNOWN_POLICY_CONFLICTS"] = []
    if stage_id == "DETERMINISTIC_VALIDATION":
        outputs["ORACLE_REWARD"] = 1
        outputs["NOP_REWARD"] = 0
        outputs["F2P_EMPIRICAL_MATRIX"] = [{"case": "f2p", "pass": True}]
        outputs["P2P_EMPIRICAL_MATRIX"] = [{"case": "p2p", "pass": True}]

    success_target = str(stage["success_transition"])
    if disposition == "ADVANCE":
        target_kind = (
            "END"
            if success_target == "END"
            else "STATE"
            if success_target in resolver.completion["state_contracts"]
            else "STAGE"
        )
        transition: dict[str, object] = {
            "action": "ADVANCE",
            "target": success_target,
            "target_kind": target_kind,
            "requires_state_validation": target_kind == "STATE",
        }
    elif disposition == "RETRY":
        transition = {
            "action": "RETRY",
            "target": stage_id,
            "target_kind": "STAGE",
            "requires_state_validation": False,
        }
    elif disposition == "BLOCK":
        transition = {
            "action": "BLOCK",
            "target": None,
            "target_kind": "NONE",
            "requires_state_validation": False,
        }
    else:
        semantics = outcome["route_statuses"][status]
        route_key = semantics.get("default_route_key") or semantics["allowed_route_keys"][0]
        transition = {
            "action": "ROUTE",
            "target": None,
            "target_kind": "ROUTE",
            "route_key": route_key,
            "route_instruction": stage["failure_routes"][route_key],
            "requires_state_validation": False,
        }

    value: dict[str, object] = {
        "schema_version": "1.0",
        "invocation_id": _invocation_id(f"{stage_id}:{attempt}"),
        "stage_id": stage_id,
        "role_id": resolver.execution_authority.primary_role_for_stage(stage_id),
        "authority": {
            "task_id": task_id,
            "task_commit": commit,
            "control_plane_commit": commit,
            "policy_versions": {},
        },
        "status": status,
        "disposition": disposition,
        "outputs": outputs,
        "evidence_refs": evidence_refs or [],
        "transition": transition,
        "validation": {
            "invocation_identity_valid": True,
            "status_legal": True,
            "output_keys_valid": True,
            "required_outputs_satisfied": status in outcome["full_output_statuses"],
            "evidence_refs_count": len(evidence_refs or []),
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
    resolver = WorkflowStateResolver(root)
    state = resolver.resolve(
        task_id="task-empty",
        task_commit=commit,
        control_plane_commit=commit,
    )
    assert state["summary"]["CURRENT"] == 0
    assert state["next"]["action"] == "INVOKE_STAGE"
    assert state["next"]["stage_id"] == "RULE_RESOLUTION"
    assert state["next"]["primary_role_id"] == "CREATION_CONTROLLER"


def test_complete_creation_chain_materializes_frozen_candidate(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    _append_through_freeze_predecessor(root, resolver, "task-freeze", commit)

    state = resolver.resolve(
        task_id="task-freeze",
        task_commit=commit,
        control_plane_commit=commit,
    )
    frozen = next(node for node in state["nodes"] if node["node_id"] == "FROZEN_CANDIDATE")
    assert frozen["status"] == "CURRENT"
    assert all(item.endswith("PASS") for item in frozen["entry_requirements"])
    assert state["next"]["action"] == "INVOKE_STAGE"
    assert state["next"]["stage_id"] == "QUALITY_INTERLOCK"


def test_task_commit_change_stales_old_chain_and_propagates(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    _append_through_freeze_predecessor(root, resolver, "task-stale", commit)

    (root / "task-change.txt").write_text("changed\n", encoding="utf-8")
    _run(root, "add", "task-change.txt")
    _run(root, "commit", "-m", "task changed")
    changed = _run(root, "rev-parse", "HEAD")

    # The control-plane snapshot intentionally remains the original contract commit.
    state = resolver.resolve(
        task_id="task-stale",
        task_commit=changed,
        control_plane_commit=commit,
    )
    first = state["nodes"][0]
    assert first["node_id"] == "RULE_RESOLUTION"
    assert first["status"] == "STALE"
    assert state["next"]["stage_id"] == "RULE_RESOLUTION"
    assert any(node["status"] == "STALE" for node in state["nodes"][1:])


def test_later_retry_supersedes_earlier_format_pass(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    ledger = _append_through_freeze_predecessor(root, resolver, "task-retry", commit)
    ledger.append(
        _record(
            resolver,
            "FORMAT_GATE",
            "task-retry",
            commit,
            attempt=2,
            status="FIXED",
        )
    )

    state = resolver.resolve(
        task_id="task-retry",
        task_commit=commit,
        control_plane_commit=commit,
    )
    format_node = next(node for node in state["nodes"] if node["node_id"] == "FORMAT_GATE")
    assert format_node["status"] == "BLOCKED"
    assert format_node["disposition"] == "RETRY"
    assert state["next"]["action"] == "RETRY_STAGE"
    assert state["next"]["stage_id"] == "FORMAT_GATE"
    assembly = next(node for node in state["nodes"] if node["node_id"] == "ASSEMBLY")
    assert assembly["status"] == "STALE"


def test_explicit_evidence_freshness_invalidates_citing_stage(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    content_hash = "sha256:" + "a" * 64
    _append_through_freeze_predecessor(
        root,
        resolver,
        "task-evidence",
        commit,
        work_package_evidence=[
            {"kind": "EXTERNAL", "ref": "external:work-package", "content_hash": content_hash}
        ],
    )

    current = resolver.resolve(
        task_id="task-evidence",
        task_commit=commit,
        control_plane_commit=commit,
    )
    assert next(node for node in current["nodes"] if node["node_id"] == "FROZEN_CANDIDATE")["status"] == "CURRENT"

    stale = resolver.resolve(
        task_id="task-evidence",
        task_commit=commit,
        control_plane_commit=commit,
        freshness_overlay={
            "schema_version": "1.0",
            "bindings": {
                "external:work-package": {
                    "status": "STALE",
                    "reason": "source was superseded",
                }
            },
        },
    )
    work = next(node for node in stale["nodes"] if node["node_id"] == "WORK_PACKAGE_RESEARCH")
    assert work["status"] == "STALE"
    assert stale["next"]["stage_id"] == "WORK_PACKAGE_RESEARCH"
    architecture = next(node for node in stale["nodes"] if node["node_id"] == "SYSTEM_ARCHITECTURE")
    assert architecture["status"] == "STALE"


def test_ledger_detects_record_tampering(tmp_path: Path) -> None:
    ledger = ExecutionLedger(tmp_path, "task-ledger")
    record = {
        "record_id": "rec_" + "1" * 64,
        "invocation_id": "inv_" + "2" * 64,
        "stage_id": "RULE_RESOLUTION",
        "authority": {
            "task_id": "task-ledger",
            "task_commit": "a" * 40,
            "control_plane_commit": "b" * 40,
        },
    }
    ledger.append(record)
    path = ledger.record_path(record["invocation_id"])
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="content hash mismatch"):
        ledger.load(validate_record_files=True)


def test_state_snapshot_is_deterministic_and_materializable(tmp_path: Path) -> None:
    root, commit = _temp_control_repo(tmp_path)
    resolver = WorkflowStateResolver(root)
    first = resolver.resolve(
        task_id="task-materialized",
        task_commit=commit,
        control_plane_commit=commit,
    )
    second = resolver.resolve(
        task_id="task-materialized",
        task_commit=commit,
        control_plane_commit=commit,
    )
    assert first == second
    path = resolver.materialize(first)
    assert path == root / ".terminus" / "workflows" / "task-materialized" / "state.json"
    assert json.loads(path.read_text(encoding="utf-8")) == first
