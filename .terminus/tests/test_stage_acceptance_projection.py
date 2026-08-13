from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.invocation import StageInvocationBuilder  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402


def test_quality_interlock_invocation_projects_q4_q6_acceptance_conditions() -> None:
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    policy = RetrievalPolicy(ROOT)
    stage = policy.stages["QUALITY_INTERLOCK"]
    inputs = {str(field): "test" for field in stage["input_contract"]["required_fields"]}
    packet = StageInvocationBuilder(ROOT, policy).build(
        InvocationContext(
            stage_id="QUALITY_INTERLOCK",
            role_id="CI_ORCHESTRATOR",
            task_id="acceptance-projection-test",
            task_commit=head,
            control_plane_commit=head,
        ),
        inputs,
    )
    checks = packet["acceptance_predicates"]["QUALITY_INTERLOCK_PASS"]
    paths = {check["path"] for check in checks}
    assert "Q4_RESULT.verdict" in paths
    assert "Q4_RESULT.evidence_status" in paths
    assert "Q6_RESULT.verdict" in paths
    assert "Q6_RESULT.evidence_status" in paths
    assert "EVIDENCE_SUFFICIENCY" in paths
