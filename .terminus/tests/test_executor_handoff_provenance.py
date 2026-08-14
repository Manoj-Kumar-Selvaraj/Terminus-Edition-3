from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.authority import ExecutionAuthority  # noqa: E402
from execution.handoff import ExecutorHandoffBuilder  # noqa: E402
from execution.invocation import StageInvocationBuilder  # noqa: E402
from execution.record import ExecutionRecordBuilder  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402


def _invocation() -> dict[str, object]:
    commit = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    policy = RetrievalPolicy(ROOT)
    stage_id = "RULE_RESOLUTION"
    role_id = ExecutionAuthority(policy).primary_role_for_stage(stage_id)
    fields = policy.stages[stage_id]["input_contract"]["required_fields"]
    return StageInvocationBuilder(ROOT, policy).build(
        InvocationContext(
            stage_id=stage_id,
            role_id=role_id,
            task_id="executor-provenance-test",
            task_commit=commit,
            control_plane_commit=commit,
        ),
        {str(field): {"test": str(field)} for field in fields},
    )


def _blocked_result(invocation: dict[str, object], handoff_id: str) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "handoff_id": handoff_id,
        "invocation_id": invocation["invocation_id"],
        "output_task_commit": invocation["authority"]["task_commit"],
        "status": "BLOCKED",
        "outputs": {},
        "evidence_refs": [],
        "blocking_reason": "provenance test",
    }


def test_recorder_accepts_canonical_manual_handoff_identity() -> None:
    invocation = _invocation()
    handoff = ExecutorHandoffBuilder(ROOT).build(invocation, executor_mode="MANUAL_CHAT")
    record = ExecutionRecordBuilder(ROOT).build(
        invocation,
        _blocked_result(invocation, str(handoff["handoff_id"])),
    )
    assert record["handoff_id"] == handoff["handoff_id"]


def test_recorder_rejects_invented_handoff_identity() -> None:
    invocation = _invocation()
    with pytest.raises(ValueError, match="does not match a canonical executor handoff"):
        ExecutionRecordBuilder(ROOT).build(
            invocation,
            _blocked_result(invocation, "handoff_" + "0" * 64),
        )
