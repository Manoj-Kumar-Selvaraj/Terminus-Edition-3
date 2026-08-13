from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.invocation import StageInvocationBuilder  # noqa: E402
from execution.record import ExecutionRecordBuilder  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402


def test_forged_acceptance_projection_is_rejected_even_with_rehashed_invocation() -> None:
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    policy = RetrievalPolicy(ROOT)
    stage = policy.stages["QUALITY_INTERLOCK"]
    invocation = StageInvocationBuilder(ROOT, policy).build(
        InvocationContext(
            stage_id="QUALITY_INTERLOCK",
            role_id="CI_ORCHESTRATOR",
            task_id="acceptance-integrity-test",
            task_commit=head,
            control_plane_commit=head,
        ),
        {
            str(field): "test"
            for field in stage["input_contract"]["required_fields"]
        },
    )

    forged = json.loads(json.dumps(invocation))
    forged["acceptance_predicates"] = {}
    identity = dict(forged)
    identity.pop("invocation_id")
    forged["invocation_id"] = StageInvocationBuilder._invocation_id(identity)

    review_pass = {
        "verdict": "PASS",
        "confidence": "MEDIUM",
        "evidence_status": "SUFFICIENT",
        "missing_evidence": [],
    }
    result = {
        "schema_version": "1.0",
        "invocation_id": forged["invocation_id"],
        "output_task_commit": head,
        "status": "QUALITY_INTERLOCK_PASS",
        "outputs": {
            "Q4_RESULT": review_pass,
            "Q6_RESULT": review_pass,
            "EVIDENCE_SUFFICIENCY": "SUFFICIENT",
        },
        "evidence_refs": [],
    }

    with pytest.raises(
        ValueError,
        match="acceptance predicate projection does not match canonical contract",
    ):
        ExecutionRecordBuilder(ROOT, policy).build(forged, result)
