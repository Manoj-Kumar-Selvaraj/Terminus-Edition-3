from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.controller_cli import _continue_payload  # noqa: E402
from execution.executor import ExecutorMode  # noqa: E402
from execution.handoff import ExecutorHandoffBuilder  # noqa: E402
from execution.invocation import StageInvocationBuilder  # noqa: E402
from execution.runner import ExecutorRunner  # noqa: E402


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _invocation() -> dict[str, object]:
    packet: dict[str, object] = {
        "schema_version": "1.0",
        "readiness": "READY",
        "stage": {
            "stage_id": "RULE_RESOLUTION",
            "role_id": "CREATION_CONTROLLER",
            "owner": "Creation Controller",
            "role_class": "CONTROLLER",
            "lifecycle": "creation",
        },
        "authority": {
            "control_plane_commit": "a" * 40,
            "task_id": "executor-test",
            "task_commit": "b" * 40,
            "policy_versions": {},
        },
        "inputs": {"required": {"CREATION_REQUEST": "test"}, "optional": {}},
        "missing_required_inputs": [],
        "ignored_input_count": 0,
        "evidence": {
            "retrieval_mode": "EXACT_ONLY",
            "mandatory_exact_reads": [".terminus/AGENT_SYSTEM.md"],
            "authorized_evidence_classes": ["CONTROL_PLANE_POLICY"],
            "excluded_evidence_classes": [],
            "evidence_required": ["rules"],
        },
        "retrieval": {
            "status": "NOT_REQUESTED",
            "query": None,
            "retrieved_context": [],
            "retrieved_chars": 0,
        },
        "output_contract": {
            "allowed_status_values": ["RULES_RESOLVED", "BLOCKED"],
            "required_fields": ["CONTROL_PLANE_COMMIT"],
            "optional_fields": [],
            "persisted_artifacts": [],
            "deterministic_validators": [],
            "semantic_reviewers": [],
        },
        "acceptance_predicates": {},
        "routing": {
            "failure_routes": {},
            "success_transition": "WORK_PACKAGE_RESEARCH",
            "stale_on": [],
        },
    }
    packet["invocation_id"] = StageInvocationBuilder._invocation_id(packet)
    return packet


def _write_executor(path: Path, *, bad_json: bool = False) -> None:
    if bad_json:
        path.write_text("print('not-json')\n", encoding="utf-8")
        return
    path.write_text(
        """import json, sys
handoff = json.load(sys.stdin)
result = {
    'schema_version': '1.0',
    'invocation_id': handoff['invocation_id'],
    'output_task_commit': 'b' * 40,
    'status': 'RULES_RESOLVED',
    'outputs': {'CONTROL_PLANE_COMMIT': 'a' * 40},
    'evidence_refs': [],
}
json.dump(result, sys.stdout)
""",
        encoding="utf-8",
    )


def test_manual_chat_handoff_is_deterministic_and_explicit() -> None:
    invocation = _invocation()
    builder = ExecutorHandoffBuilder()
    first = builder.build(invocation, executor_mode=ExecutorMode.MANUAL_CHAT)
    second = builder.build(invocation, executor_mode=ExecutorMode.MANUAL_CHAT)
    assert first["handoff_id"] == second["handoff_id"]
    assert first["executor_mode"] == "MANUAL_CHAT"
    assert first["invocation_id"] == invocation["invocation_id"]
    assert "DO:" in first["handoff_text"]
    assert "DO NOT:" in first["handoff_text"]
    assert "Return exactly one JSON object" in first["handoff_text"]
    assert any("next workflow stage" in item for item in first["do_not"])
    assert any("execution records" in item for item in first["do_not"])


def test_tampered_invocation_is_rejected_before_handoff() -> None:
    invocation = _invocation()
    invocation["stage"]["role_id"] = "CI_ORCHESTRATOR"
    with pytest.raises(ValueError, match="invocation_id does not match"):
        ExecutorHandoffBuilder().build(invocation, executor_mode="MANUAL_CHAT")


def test_non_ready_invocation_is_not_executable() -> None:
    invocation = _invocation()
    invocation["readiness"] = "BLOCKED_MISSING_INPUTS"
    identity = dict(invocation)
    identity.pop("invocation_id")
    invocation["invocation_id"] = StageInvocationBuilder._invocation_id(identity)
    with pytest.raises(ValueError, match="requires a READY"):
        ExecutorHandoffBuilder().build(invocation, executor_mode="MANUAL_CHAT")


def test_local_command_round_trip_is_shell_free_and_non_mutating(tmp_path: Path) -> None:
    script = tmp_path / "executor.py"
    _write_executor(script)
    response = ExecutorRunner(ROOT).run_local(
        _invocation(),
        [sys.executable, str(script)],
        timeout_seconds=10,
    )
    assert response["status"] == "EXECUTED"
    assert response["command"]["shell"] is False
    assert response["stage_result"]["status"] == "RULES_RESOLVED"
    assert response["recorded"] is False
    assert response["workflow_state_mutated"] is False


def test_local_command_rejects_non_json_result(tmp_path: Path) -> None:
    script = tmp_path / "bad.py"
    _write_executor(script, bad_json=True)
    response = ExecutorRunner(ROOT).run_local(
        _invocation(),
        [sys.executable, str(script)],
        timeout_seconds=10,
    )
    assert response["status"] == "INVALID_RESULT"
    assert response["stage_result"] is None


def test_local_command_rejects_wrong_result_invocation_id(tmp_path: Path) -> None:
    script = tmp_path / "wrong.py"
    script.write_text(
        """import json, sys
json.load(sys.stdin)
json.dump({'schema_version':'1.0','invocation_id':'inv_' + '0'*64,'output_task_commit':'b'*40,'status':'BLOCKED','outputs':{},'evidence_refs':[]}, sys.stdout)
""",
        encoding="utf-8",
    )
    response = ExecutorRunner(ROOT).run_local(
        _invocation(),
        [sys.executable, str(script)],
        timeout_seconds=10,
    )
    assert response["status"] == "INVALID_RESULT"
    assert "does not match handoff" in response["stderr_summary"]


def test_prepare_is_non_mutating() -> None:
    prepared = ExecutorRunner(ROOT).prepare(_invocation())
    assert prepared["status"] == "PREPARED"
    assert prepared["stage_result"] is None
    assert prepared["recorded"] is False
    assert prepared["workflow_state_mutated"] is False


def test_controller_continue_can_prepare_manual_handoff(tmp_path: Path) -> None:
    commit = _head()
    inputs = tmp_path / "inputs.json"
    inputs.write_text(json.dumps({"CREATION_REQUEST": "executor bridge test"}), encoding="utf-8")
    args = SimpleNamespace(
        task_id="executor-controller-test",
        task_commit=commit,
        control_plane_commit=commit,
        inputs_json=str(inputs),
        query=None,
        db=None,
        retrieval_limit=10,
        max_chars=30000,
        prepare_executor="MANUAL_CHAT",
    )
    snapshot = {
        "state_snapshot_id": "state_test",
        "next": {
            "action": "INVOKE_STAGE",
            "stage_id": "RULE_RESOLUTION",
            "primary_role_id": "CREATION_CONTROLLER",
        },
    }
    payload = _continue_payload(ROOT, args, snapshot)
    assert payload["invocation"]["readiness"] == "READY"
    assert payload["executor_handoff"]["executor_mode"] == "MANUAL_CHAT"
    assert (
        payload["executor_handoff"]["invocation_id"]
        == payload["invocation"]["invocation_id"]
    )


def test_external_await_never_prepares_executor_handoff() -> None:
    args = SimpleNamespace(prepare_executor="MANUAL_CHAT")
    snapshot = {
        "state_snapshot_id": "state_external",
        "next": {
            "action": "AWAIT_EXTERNAL_GATE",
            "stage_id": "HARBOR_LLMAJ",
            "external_run_id": "run-42",
        },
    }
    payload = _continue_payload(ROOT, args, snapshot)
    assert payload["invocation"] is None
    assert payload["executor_handoff"] is None
    assert payload["dispatch"]["status"] == "AWAITING_EXTERNAL_RESULT"
