from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from human_decision import HumanDecisionStore  # noqa: E402
import q4_chat_human_risk  # noqa: E402
from execution.acceptance import StageAcceptancePredicates  # noqa: E402


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _q4() -> dict[str, object]:
    return {
        "role": "Spec-Test Contract Reviewer",
        "verdict": "REVISE",
        "confidence": "HIGH",
        "evidence_status": "SUFFICIENT",
        "missing_evidence": [],
        "task": "risk-task",
        "task_commit": _head(),
        "review_id": "risk-task-review-1",
        "role_output": {"BLOCKING_FINDING_IDS": ["F01"]},
    }


def _resolved_decision(root: Path, *, commit: str | None = None, findings=None):
    accepted_commit = commit or _head()
    store = HumanDecisionStore(root)
    event = store.request(
        task_id="risk-task",
        task_commit=accepted_commit,
        stage="QUALITY_INTERLOCK",
        decision_type="ACCEPT_RESIDUAL_Q4_RISK",
        allowed_decisions=["ACCEPT_RISK", "REJECT"],
        reason="F01 remains after Q4 budget exhaustion.",
        consequences="Q4 remains REVISE; F01 remains tracked in issue #66.",
        context={
            "q4_review_id": "risk-task-review-1",
            "q4_task_commit": _head(),
            "q4_verdict": "REVISE",
            "accepted_finding_ids": findings if findings is not None else ["F01"],
            "residual_backlog": ["issue #66"],
        },
    )
    return store.resolve(
        decision_id=event["request"]["decision_id"],
        decision="ACCEPT_RISK",
        response_text="Yes, accept the residual risk and continue.",
    )


def test_chat_human_q4_acceptance_preserves_revise(tmp_path: Path, monkeypatch) -> None:
    event = _resolved_decision(tmp_path)
    decision_id = event["request"]["decision_id"]
    monkeypatch.setattr(q4_chat_human_risk, "HumanDecisionStore", lambda root: HumanDecisionStore(tmp_path))
    result = q4_chat_human_risk.validate_chat_human_risk_acceptance(
        ROOT,
        envelope={"type": q4_chat_human_risk.SATISFACTION_MODE, "decision_id": decision_id},
        q4_result=_q4(),
        current_task_commit_override=_head(),
    )
    assert result["satisfaction"] == "CHAT_HUMAN_RISK_ACCEPTANCE"
    assert result["authority"] == "CHAT_HUMAN_APPROVAL"
    assert result["q4_verdict"] == "REVISE"


def test_incomplete_finding_acceptance_fails(tmp_path: Path, monkeypatch) -> None:
    event = _resolved_decision(tmp_path, findings=[])
    decision_id = event["request"]["decision_id"]
    monkeypatch.setattr(q4_chat_human_risk, "HumanDecisionStore", lambda root: HumanDecisionStore(tmp_path))
    with pytest.raises(ValueError, match="every blocking Q4 finding"):
        q4_chat_human_risk.validate_chat_human_risk_acceptance(
            ROOT,
            envelope={"type": q4_chat_human_risk.SATISFACTION_MODE, "decision_id": decision_id},
            q4_result=_q4(),
            current_task_commit_override=_head(),
        )


def test_stage_acceptance_recognizes_chat_human_route(monkeypatch) -> None:
    outputs = {
        "Q4_SATISFACTION": q4_chat_human_risk.SATISFACTION_MODE,
        "Q4_RESULT": _q4(),
        "Q4_CLOSURE_RESULT": {
            "type": q4_chat_human_risk.SATISFACTION_MODE,
            "decision_id": "hd_" + "a" * 64,
        },
    }
    monkeypatch.setattr(
        "execution.acceptance.validate_chat_human_risk_acceptance",
        lambda root, *, envelope, q4_result: {"satisfaction": q4_chat_human_risk.SATISFACTION_MODE},
    )
    assert StageAcceptancePredicates._q4_satisfied(outputs, ROOT)
