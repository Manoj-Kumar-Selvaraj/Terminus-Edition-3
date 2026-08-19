from __future__ import annotations

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
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _temp_control_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", "--quiet", "--shared", str(ROOT), str(root)],
        check=True,
    )
    _run(root, "config", "user.email", "terminus-tests@example.invalid")
    _run(root, "config", "user.name", "Terminus Tests")
    return root, _run(root, "rev-parse", "HEAD")


def _rule_resolution_record(
    root: Path,
    resolver: WorkflowStateResolver,
    *,
    task_id: str,
    task_commit: str,
    control_commit: str,
) -> dict[str, object]:
    role_id = resolver.execution_authority.primary_role_for_stage("RULE_RESOLUTION")
    invocation = StageInvocationBuilder(root, resolver.policy).build(
        InvocationContext(
            stage_id="RULE_RESOLUTION",
            role_id=role_id,
            task_id=task_id,
            task_commit=task_commit,
            control_plane_commit=control_commit,
        ),
        {"CREATION_REQUEST": "fixture creation request"},
    )
    result = {
        "schema_version": "1.0",
        "invocation_id": invocation["invocation_id"],
        "output_task_commit": task_commit,
        "status": "RULES_RESOLVED",
        "outputs": {
            "CONTROL_PLANE_COMMIT": control_commit,
            "RULE_SOURCES": ["TERMINUS_3_AI_INSTRUCTIONS.md"],
            "ACTIVE_VALIDATORS": [".terminus/validate_agent_system.py"],
            "CREATION_PROFILE": "large_system_strict",
            "NETWORK_ENVIRONMENT_CONSTRAINTS": "repository-default",
            "KNOWN_POLICY_CONFLICTS": [],
        },
        "evidence_refs": [],
    }
    return ExecutionRecordBuilder(root, resolver.policy).build(invocation, result)


def _semantically_identical_new_control_commit(root: Path) -> str:
    path = root / ".terminus" / "agents" / "stage_contracts.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(
        json.dumps(payload, indent=4, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _run(root, "add", ".terminus/agents/stage_contracts.json")
    _run(root, "commit", "-m", "Change stage-contract snapshot bytes")
    return _run(root, "rev-parse", "HEAD")


def test_historical_record_survives_control_plane_change_and_can_be_superseded(
    tmp_path: Path,
) -> None:
    root, old_control = _temp_control_repo(tmp_path)
    task_id = "historical-ledger-replay"
    task_commit = old_control

    old_resolver = WorkflowStateResolver(root)
    ledger = ExecutionLedger(root, task_id)
    old_record = _rule_resolution_record(
        root,
        old_resolver,
        task_id=task_id,
        task_commit=task_commit,
        control_commit=old_control,
    )
    old_event = ledger.append(old_record)

    new_control = _semantically_identical_new_control_commit(root)
    assert new_control != old_control

    # Historical immutable evidence must remain readable even though its original
    # control-plane bytes no longer match the contracts loaded from the new HEAD.
    loaded = ledger.load(validate_record_files=True)
    assert [event["event_id"] for event in loaded] == [old_event["event_id"]]

    new_resolver = WorkflowStateResolver(root)
    stale_state = new_resolver.resolve(
        task_id=task_id,
        task_commit=task_commit,
        control_plane_commit=new_control,
    )
    assert stale_state["nodes"][0]["node_id"] == "RULE_RESOLUTION"
    assert stale_state["nodes"][0]["status"] == "STALE"
    assert stale_state["next"]["action"] == "INVOKE_STAGE"
    assert stale_state["next"]["stage_id"] == "RULE_RESOLUTION"

    fresh_record = _rule_resolution_record(
        root,
        new_resolver,
        task_id=task_id,
        task_commit=task_commit,
        control_commit=new_control,
    )
    fresh_event = ledger.append(fresh_record)
    assert fresh_event["sequence"] == 2

    advanced = new_resolver.resolve(
        task_id=task_id,
        task_commit=task_commit,
        control_plane_commit=new_control,
    )
    assert advanced["nodes"][0]["status"] == "CURRENT"
    assert advanced["next"]["action"] == "INVOKE_STAGE"
    assert advanced["next"]["stage_id"] == "WORK_PACKAGE_RESEARCH"
