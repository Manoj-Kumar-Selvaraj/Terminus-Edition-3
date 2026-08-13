#!/usr/bin/env python3
"""Validate workflow-state materialization and execution-ledger contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.ledger import ExecutionLedger  # noqa: E402
from execution.state import WorkflowStateResolver  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"Terminus workflow-state validation FAILED: {message}")


def main() -> int:
    contract = json.loads((ROOT / ".terminus/agents/workflow_state_contract.json").read_text(encoding="utf-8"))
    if contract.get("workflow_state_version") != "1.0" or contract.get("ledger_version") != "1.0":
        fail("workflow-state and ledger versions must remain 1.0")
    if contract.get("stage_status_values") != ["CURRENT", "STALE", "MISSING", "BLOCKED"]:
        fail("workflow stage status vocabulary drift")
    expected_actions = {"INVOKE_STAGE", "RETRY_STAGE", "ROUTE", "BLOCKED", "VALIDATE_STATE", "END"}
    if set(contract.get("next_action_values", [])) != expected_actions:
        fail("workflow next-action vocabulary is incomplete")

    required_paths = [
        ".terminus/agents/WORKFLOW_STATE.md",
        ".terminus/agents/stage_acceptance_predicates.json",
        ".terminus/agents/schemas/execution_ledger_event.schema.json",
        ".terminus/agents/schemas/evidence_freshness.schema.json",
        ".terminus/agents/schemas/workflow_state.schema.json",
        ".terminus/execution/ledger.py",
        ".terminus/execution/state.py",
        ".terminus/execution/controller_cli.py",
        ".terminus/tests/test_workflow_state.py",
        ".terminus/tests/test_workflow_temporal_order.py",
        ".terminus/tests/test_retrieval_workflow_state_exclusion.py",
    ]
    missing = [path for path in required_paths if not (ROOT / path).is_file()]
    if missing:
        fail(f"missing workflow-state files: {missing}")

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    if ".terminus/workflows/" not in gitignore:
        fail("derived .terminus/workflows/ state must remain ignored/rebuildable")
    if ".terminus/executions/" in gitignore:
        fail("durable .terminus/executions/ provenance must not be ignored")

    policy = (ROOT / ".terminus/agents/WORKFLOW_STATE.md").read_text(encoding="utf-8").lower()
    markers = [
        "materialized state file into acceptance evidence",
        "last valid ledger event for that stage",
        "downstream acceptance cannot survive a non-current predecessor",
        "task commit lineage",
        "unattributed task change",
        "frozen_candidate",
        "legacy `.terminus/sessions/<task>.md`",
        "normal chatgpt conversation",
    ]
    for marker in markers:
        if marker not in policy:
            fail(f"WORKFLOW_STATE.md missing required invariant marker: {marker}")

    state_code = (ROOT / ".terminus/execution/state.py").read_text(encoding="utf-8")
    for marker in (
        "last_current_stage_sequence",
        "predates the latest current predecessor execution",
        "expected_input_task_commit",
        "UNATTRIBUTED_CHANGE",
        "acceptance.validate",
    ):
        if marker not in state_code:
            fail(f"state resolver missing lineage/acceptance marker: {marker}")
    controller_code = (ROOT / ".terminus/execution/controller_cli.py").read_text(encoding="utf-8")
    if 'lineage.get("output_task_commit")' not in controller_code:
        fail("controller record flow must rematerialize at output_task_commit")

    state_schema = json.loads((ROOT / ".terminus/agents/schemas/workflow_state.schema.json").read_text(encoding="utf-8"))
    if state_schema.get("$id") != "terminus-workflow-state-v1" or "lineage" not in state_schema.get("required", []):
        fail("workflow state schema must require lineage")
    ledger_schema = json.loads((ROOT / ".terminus/agents/schemas/execution_ledger_event.schema.json").read_text(encoding="utf-8"))
    required_ledger = set(ledger_schema.get("required", []))
    if not {"input_task_commit", "output_task_commit"} <= required_ledger or "task_commit" in required_ledger:
        fail("ledger event schema must bind explicit input/output task commits")

    resolver = WorkflowStateResolver(ROOT)
    if len(resolver.policy.stages) != 23 or len(resolver.chain) != 24:
        fail("workflow resolver must expose 23 stages plus FROZEN_CANDIDATE")
    if resolver.chain[0] != {"node_id": "RULE_RESOLUTION", "node_kind": "STAGE"}:
        fail("workflow chain must start at RULE_RESOLUTION")
    if resolver.chain[-1] != {"node_id": "SUBMISSION_READY", "node_kind": "STAGE"}:
        fail("workflow chain must end at SUBMISSION_READY")

    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    snapshot = resolver.resolve(
        task_id="workflow-validator-no-ledger",
        task_commit=head,
        control_plane_commit=head,
    )
    if snapshot["next"].get("stage_id") != "RULE_RESOLUTION" or snapshot["next"].get("action") != "INVOKE_STAGE":
        fail("empty ledger must start with RULE_RESOLUTION")
    if snapshot["lineage"].get("status") != "UNINITIALIZED":
        fail("empty ledger must expose UNINITIALIZED lineage")

    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        ledger = ExecutionLedger(temp_root, "ledger-validator")
        record = {
            "record_id": "rec_" + "1" * 64,
            "invocation_id": "inv_" + "2" * 64,
            "stage_id": "RULE_RESOLUTION",
            "authority": {
                "task_id": "ledger-validator",
                "task_commit": "a" * 40,
                "control_plane_commit": "b" * 40,
            },
            "task_lineage": {
                "input_task_commit": "a" * 40,
                "output_task_commit": "a" * 40,
                "task_changed": False,
            },
        }
        first = ledger.append(record)
        second = ledger.append(record)
        if first != second:
            fail("re-appending the same immutable record must be idempotent")
        events = ledger.load(validate_record_files=True)
        if len(events) != 1 or events[0]["sequence"] != 1:
            fail("ledger must contain exactly one idempotently appended event")
        if events[0]["input_task_commit"] != "a" * 40 or events[0]["output_task_commit"] != "a" * 40:
            fail("ledger event did not persist task commit lineage")

    print("Terminus workflow-state validation PASS")
    print(
        "workflow_state=1.0 ledger=1.0 stages=23 nodes=24 "
        "record_selection=last_event staleness=evidence_temporal_dependency "
        "commit_lineage=input_output unattributed_changes=blocked predicates=revalidated "
        "freeze=derived_state next=deterministic durable=executions derived=workflows_ignored "
        "legacy_sessions=not_inferred portability=normal_chatgpt_fallback"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
