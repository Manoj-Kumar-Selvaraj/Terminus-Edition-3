from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))
sys.path.insert(0, str(ROOT / ".terminus" / "tests"))

from authority_helpers import sign_receipt  # noqa: E402
from execution.acceptance import StageAcceptancePredicates  # noqa: E402
from feedback.ingestion import FeedbackIngestor  # noqa: E402
from feedback.registry import LearningStore  # noqa: E402
import q4_human_risk  # noqa: E402


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _store(tmp_path: Path) -> LearningStore:
    return LearningStore(
        ROOT,
        state_root=tmp_path / "state",
        knowledge_root=tmp_path / "knowledge",
    )


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
        "role_output": {"BLOCKING_FINDING_IDS": ["Q4-001", "Q4-002"]},
    }


def _capture(
    store: LearningStore,
    *,
    producer: str = "alice",
    category: str = "HUMAN_RISK_ACCEPTANCE",
    task_id: str = "risk-task",
    task_commit: str | None = None,
    accepted: list[str] | None = None,
    authenticated: bool = True,
) -> dict[str, object]:
    commit = task_commit or _head()
    accepted_ids = accepted if accepted is not None else ["Q4-001", "Q4-002"]
    captured_at = "2026-08-20T09:00:00Z"
    source = {"type": "HUMAN_REVIEW", "producer": producer}
    observation = {
        "severity": "HIGH",
        "message": "I accept the exact residual Q4 risk for this task snapshot.",
        "category": category,
        "stage_hint": "QUALITY_INTERLOCK",
        "value": {
            "decision": "ACCEPTED",
            "q4_verdict": "REVISE",
            "q4_review_id": "risk-task-review-1",
            "accepted_finding_ids": accepted_ids,
            "residual_backlog": ["issue #66"],
        },
    }
    claim = FeedbackIngestor.authority_claim(
        source=source,
        task={"task_id": task_id, "task_commit": commit},
        observation=observation,
        captured_at=captured_at,
        source_binding=None,
    )
    receipt = (
        sign_receipt("HUMAN_FEEDBACK", f"human:{producer}", claim)
        if authenticated
        else None
    )
    return FeedbackIngestor(ROOT, store=store).capture(
        source_type="HUMAN_REVIEW",
        producer=producer,
        task_id=task_id,
        task_commit=commit,
        severity="HIGH",
        message=observation["message"],
        category=category,
        stage_hint="QUALITY_INTERLOCK",
        value=observation["value"],
        captured_at=captured_at,
        authority_receipt=receipt,
    )


def _envelope(event: dict[str, object]) -> dict[str, object]:
    return {
        "type": q4_human_risk.SATISFACTION_MODE,
        "feedback_id": event["feedback_id"],
    }


def test_authenticated_human_risk_acceptance_validates(tmp_path: Path) -> None:
    store = _store(tmp_path)
    event = _capture(store)
    result = q4_human_risk.validate_human_risk_acceptance(
        ROOT,
        envelope=_envelope(event),
        q4_result=_q4(),
        store=store,
    )
    assert result["satisfaction"] == "AUTHENTICATED_HUMAN_RISK_ACCEPTANCE"
    assert result["q4_verdict"] == "REVISE"
    assert result["accepted_finding_ids"] == ["Q4-001", "Q4-002"]


def test_wrong_task_or_commit_cannot_reuse_acceptance(tmp_path: Path) -> None:
    store = _store(tmp_path)
    event = _capture(store)
    wrong_task = copy.deepcopy(_q4())
    wrong_task["task"] = "other-task"
    with pytest.raises(ValueError, match="exact Q4 task commit"):
        q4_human_risk.validate_human_risk_acceptance(
            ROOT,
            envelope=_envelope(event),
            q4_result=wrong_task,
            store=store,
        )

    wrong_commit = copy.deepcopy(_q4())
    wrong_commit["task_commit"] = "0" * 40
    with pytest.raises(ValueError, match="exact Q4 task commit"):
        q4_human_risk.validate_human_risk_acceptance(
            ROOT,
            envelope=_envelope(event),
            q4_result=wrong_commit,
            store=store,
        )


def test_wrong_category_or_incomplete_finding_set_is_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wrong_category = _capture(store, category="FINDING_VERIFICATION")
    with pytest.raises(ValueError, match="wrong category"):
        q4_human_risk.validate_human_risk_acceptance(
            ROOT,
            envelope=_envelope(wrong_category),
            q4_result=_q4(),
            store=store,
        )

    store2 = _store(tmp_path / "second")
    incomplete = _capture(store2, accepted=["Q4-001"])
    with pytest.raises(ValueError, match="every blocking Q4 finding"):
        q4_human_risk.validate_human_risk_acceptance(
            ROOT,
            envelope=_envelope(incomplete),
            q4_result=_q4(),
            store=store2,
        )


def test_unauthenticated_or_machine_authored_acceptance_is_rejected(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    asserted = _capture(store, authenticated=False)
    with pytest.raises(ValueError, match="not authoritative"):
        q4_human_risk.validate_human_risk_acceptance(
            ROOT,
            envelope=_envelope(asserted),
            q4_result=_q4(),
            store=store,
        )

    machine_store = _store(tmp_path / "machine")
    machine = _capture(machine_store, producer="CI_ORCHESTRATOR")
    with pytest.raises(ValueError, match="machine role"):
        q4_human_risk.validate_human_risk_acceptance(
            ROOT,
            envelope=_envelope(machine),
            q4_result=_q4(),
            store=machine_store,
        )


def test_stage_acceptance_route_is_explicit_and_keeps_q4_revise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predicate = StageAcceptancePredicates(ROOT)
    q4 = _q4()
    envelope = {
        "type": q4_human_risk.SATISFACTION_MODE,
        "feedback_id": "feedback_" + "a" * 64,
    }
    called: dict[str, object] = {}

    def fake_validate(root: Path, *, envelope, q4_result):
        called["root"] = root
        called["envelope"] = envelope
        called["q4"] = q4_result
        return {"satisfaction": q4_human_risk.SATISFACTION_MODE}

    monkeypatch.setattr("execution.acceptance.validate_human_risk_acceptance", fake_validate)
    assert predicate._q4_satisfied(
        {
            "Q4_SATISFACTION": q4_human_risk.SATISFACTION_MODE,
            "Q4_RESULT": q4,
            "Q4_CLOSURE_RESULT": envelope,
        }
    )
    assert called["q4"]["verdict"] == "REVISE"
