from __future__ import annotations

import copy
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.authority import ExecutionAuthority  # noqa: E402
from execution.controller_cli import _continue_payload  # noqa: E402
from execution.executor import ExecutorMode  # noqa: E402
from execution.handoff import ExecutorHandoffBuilder  # noqa: E402
from execution.invocation import StageInvocationBuilder  # noqa: E402
from execution.record import ExecutionRecordBuilder  # noqa: E402
from execution.runner import ExecutorRunner  # noqa: E402
from execution.schema_validation import ExecutorSchemaValidator  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _invocation(stage_id: str = "RULE_RESOLUTION") -> dict[str, object]:
    commit = _head()
    policy = RetrievalPolicy(ROOT)
    role_id = ExecutionAuthority(policy).primary_role_for_stage(stage_id)
    required = policy.stages[stage_id]["input_contract"]["required_fields"]
    inputs = {str(field): {"test": str(field)} for field in required}
    return StageInvocationBuilder(ROOT, policy).build(
        InvocationContext(
            stage_id=stage_id,
            role_id=role_id,
            task_id="executor-test",
            task_commit=commit,
            control_plane_commit=commit,
        ),
        inputs,
    )


def _rehash(packet: dict[str, object]) -> None:
    identity = dict(packet)
    identity.pop("invocation_id", None)
    packet["invocation_id"] = StageInvocationBuilder._invocation_id(identity)


def test_manual_chat_handoff_is_deterministic_and_explicit() -> None:
    invocation = _invocation()
    builder = ExecutorHandoffBuilder(ROOT)
    first = builder.build(invocation, executor_mode=ExecutorMode.MANUAL_CHAT)
    second = builder.build(invocation, executor_mode=ExecutorMode.MANUAL_CHAT)
    assert first["handoff_id"] == second["handoff_id"]
    assert first["executor_mode"] == "MANUAL_CHAT"
    assert first["invocation_id"] == invocation["invocation_id"]
    assert "DO:" in first["handoff_text"]
    assert "DO NOT:" in first["handoff_text"]
    assert "handoff_id" in first["result_contract"]["required_top_level_fields"]
    assert any("next workflow stage" in item for item in first["do_not"])


def test_rehashed_evidence_widening_is_rejected_before_handoff() -> None:
    invocation = copy.deepcopy(_invocation())
    invocation["evidence"]["authorized_evidence_classes"].append("SOLVER_VISIBLE_TASK")
    _rehash(invocation)
    with pytest.raises(ValueError, match="authorized evidence classes"):
        ExecutorHandoffBuilder(ROOT).build(invocation, executor_mode="MANUAL_CHAT")


def test_rehashed_role_change_is_rejected_before_handoff() -> None:
    invocation = copy.deepcopy(_invocation())
    invocation["stage"]["role_id"] = "CI_ORCHESTRATOR"
    _rehash(invocation)
    with pytest.raises(ValueError, match="not authorized to execute"):
        ExecutorHandoffBuilder(ROOT).build(invocation, executor_mode="MANUAL_CHAT")


def test_rehashed_routing_change_is_rejected_before_handoff() -> None:
    invocation = copy.deepcopy(_invocation())
    invocation["routing"]["success_transition"] = "END"
    _rehash(invocation)
    with pytest.raises(ValueError, match="routing does not match canonical"):
        ExecutorHandoffBuilder(ROOT).build(invocation, executor_mode="MANUAL_CHAT")


def test_rehashed_unauthorized_retrieval_is_rejected_before_handoff() -> None:
    invocation = copy.deepcopy(_invocation())
    content = "private oracle content"
    invocation["retrieval"] = {
        "status": "INDEXED_CONTEXT",
        "query": "oracle",
        "retrieved_context": [
            {
                "source_kind": "SOLUTION_ORACLE",
                "evidence_class": "SOLUTION_ORACLE",
                "source_path": "executor-test/solution/solve.py",
                "content": content,
                "content_hash": "sha256:"
                + __import__("hashlib").sha256(content.encode()).hexdigest(),
                "truncated": False,
            }
        ],
        "retrieved_chars": len(content),
    }
    _rehash(invocation)
    with pytest.raises(ValueError, match="evidence class is not authorized"):
        ExecutorHandoffBuilder(ROOT).build(invocation, executor_mode="MANUAL_CHAT")


def test_local_command_rejects_mutating_role_class() -> None:
    with pytest.raises(ValueError, match="read-only.*PRODUCER/FIXER"):
        ExecutorHandoffBuilder(ROOT).build(
            _invocation("WORK_PACKAGE_RESEARCH"),
            executor_mode=ExecutorMode.LOCAL_COMMAND,
        )


@pytest.mark.skipif(
    platform.system() != "Linux" or shutil.which("bwrap") is None,
    reason="bubblewrap sandbox is required",
)
def test_local_command_is_sandboxed_read_only_and_repo_hidden() -> None:
    invocation = _invocation()
    protected = str(ROOT / ".terminus" / "AGENT_SYSTEM.md")
    code = f"""import json, os, sys
handoff = json.load(sys.stdin)
write_ok = True
try:
    open('/workspace/probe.txt', 'w').write('x')
except OSError:
    write_ok = False
json.dump({{
    'schema_version':'1.0',
    'handoff_id':handoff['handoff_id'],
    'invocation_id':handoff['invocation_id'],
    'output_task_commit':handoff['authority']['task_commit'],
    'status':'BLOCKED',
    'outputs':{{'repo_visible':os.path.exists({protected!r}),'write_ok':write_ok}},
    'evidence_refs':[],
    'blocking_reason':'transport test'
}}, sys.stdout)
"""
    response = ExecutorRunner(ROOT).run_local(
        invocation,
        [sys.executable, "-c", code],
        timeout_seconds=20,
    )
    assert response["status"] == "EXECUTED"
    assert response["command"]["shell"] is False
    assert response["sandbox"]["backend"] == "BWRAP"
    assert response["sandbox"]["read_only"] is True
    assert response["sandbox"]["authoritative_repository_mounted"] is False
    assert response["stage_result"]["outputs"]["repo_visible"] is False
    assert response["stage_result"]["outputs"]["write_ok"] is False


@pytest.mark.skipif(
    platform.system() != "Linux" or shutil.which("bwrap") is None,
    reason="bubblewrap sandbox is required",
)
def test_local_command_enforces_live_output_limit() -> None:
    response = ExecutorRunner(ROOT).run_local(
        _invocation(),
        [sys.executable, "-c", "import sys; sys.stdout.write('x' * 2000000)"],
        timeout_seconds=20,
    )
    assert response["status"] == "OUTPUT_LIMIT_EXCEEDED"
    assert response["stage_result"] is None


def test_executor_stage_result_requires_exact_handoff_id() -> None:
    handoff = ExecutorHandoffBuilder(ROOT).build(
        _invocation(), executor_mode=ExecutorMode.MANUAL_CHAT
    )
    result = {
        "schema_version": "1.0",
        "handoff_id": "handoff_" + "0" * 64,
        "invocation_id": handoff["invocation_id"],
        "output_task_commit": handoff["authority"]["task_commit"],
        "status": "BLOCKED",
        "outputs": {},
        "evidence_refs": [],
        "blocking_reason": "test",
    }
    from execution.executor import validate_stage_result_shape

    with pytest.raises(ValueError, match="handoff_id does not match"):
        validate_stage_result_shape(
            result,
            invocation_id=str(handoff["invocation_id"]),
            handoff_id=str(handoff["handoff_id"]),
        )


def test_handoff_id_is_persisted_in_execution_record() -> None:
    invocation = _invocation()
    handoff = ExecutorHandoffBuilder(ROOT).build(
        invocation, executor_mode=ExecutorMode.MANUAL_CHAT
    )
    result = {
        "schema_version": "1.0",
        "handoff_id": handoff["handoff_id"],
        "invocation_id": invocation["invocation_id"],
        "output_task_commit": invocation["authority"]["task_commit"],
        "status": "BLOCKED",
        "outputs": {},
        "evidence_refs": [],
        "blocking_reason": "test block",
    }
    record = ExecutionRecordBuilder(ROOT).build(invocation, result)
    assert record["handoff_id"] == handoff["handoff_id"]


def test_runtime_schema_validation_rejects_invalid_handoff() -> None:
    validator = ExecutorSchemaValidator(ROOT)
    handoff = ExecutorHandoffBuilder(ROOT).build(
        _invocation(), executor_mode=ExecutorMode.MANUAL_CHAT
    )
    bad = dict(handoff)
    bad["unexpected"] = True
    with pytest.raises(ValueError, match="schema validation failed"):
        validator.validate_handoff(bad)


def test_prepare_is_non_mutating() -> None:
    prepared = ExecutorRunner(ROOT).prepare(_invocation())
    assert prepared["status"] == "PREPARED"
    assert prepared["stage_result"] is None
    assert prepared["recorded"] is False
    assert prepared["workflow_state_mutated"] is False


def test_controller_continue_can_prepare_manual_handoff(tmp_path: Path) -> None:
    commit = _head()
    inputs = tmp_path / "inputs.json"
    inputs.write_text(
        json.dumps({"CREATION_REQUEST": "executor bridge test"}), encoding="utf-8"
    )
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
    assert payload["executor_handoff"]["invocation_id"] == payload["invocation"]["invocation_id"]


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
