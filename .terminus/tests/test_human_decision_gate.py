from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from human_decision import HumanDecisionStore  # noqa: E402


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _request(store: HumanDecisionStore):
    return store.request(
        task_id="risk-task",
        task_commit=_head(),
        stage="QUALITY_INTERLOCK",
        decision_type="ACCEPT_RESIDUAL_Q4_RISK",
        allowed_decisions=["ACCEPT_RISK", "REJECT"],
        reason="Residual Q4 blocker remains.",
        consequences="Q4 remains REVISE and the risk stays in backlog.",
        context={"q4_review_id": "review-1"},
    )


def test_request_is_deterministic_and_resolution_is_commit_bound(tmp_path: Path) -> None:
    store = HumanDecisionStore(tmp_path)
    first = _request(store)
    second = _request(store)
    assert first["request"]["decision_id"] == second["request"]["decision_id"]
    assert len(store.outstanding(task_id="risk-task", task_commit=_head())) == 1

    resolved = store.resolve(
        decision_id=first["request"]["decision_id"],
        decision="ACCEPT_RISK",
        response_text="Accept the risk and continue.",
    )
    assert resolved["resolution"]["authority"]["type"] == "CHAT_HUMAN_APPROVAL"
    assert resolved["resolution"]["authority"]["source"] == "ACTIVE_TASK_CHAT"
    assert store.outstanding(task_id="risk-task", task_commit=_head()) == []

    with pytest.raises(ValueError, match="stale"):
        store.require_resolved(
            decision_id=first["request"]["decision_id"],
            task_id="risk-task",
            task_commit="0" * 40,
            stage="QUALITY_INTERLOCK",
            decision_type="ACCEPT_RESIDUAL_Q4_RISK",
            accepted_decisions={"ACCEPT_RISK"},
        )


def test_resolution_requires_allowed_choice_and_active_task_chat(tmp_path: Path) -> None:
    store = HumanDecisionStore(tmp_path)
    event = _request(store)
    decision_id = event["request"]["decision_id"]
    with pytest.raises(ValueError, match="not allowed"):
        store.resolve(
            decision_id=decision_id,
            decision="OTHER",
            response_text="Other",
        )
    with pytest.raises(ValueError, match="ACTIVE_TASK_CHAT"):
        store.resolve(
            decision_id=decision_id,
            decision="ACCEPT_RISK",
            response_text="Accept",
            source="OTHER_SOURCE",
        )
