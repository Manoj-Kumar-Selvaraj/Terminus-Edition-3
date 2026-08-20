"""Validate same-chat human risk acceptance for a frozen Q4 REVISE."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from human_decision import HumanDecisionStore
from review_contract import current_task_commit

SATISFACTION_MODE = "CHAT_HUMAN_RISK_ACCEPTANCE"
DECISION_TYPE = "ACCEPT_RESIDUAL_Q4_RISK"
GATE_STAGE = "QUALITY_INTERLOCK"


def _require_ancestor(root: Path, ancestor: str, descendant: str) -> None:
    check = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True,
    )
    if check.returncode != 0:
        raise ValueError("current accepted task commit must equal or descend from the frozen Q4 task commit")


def validate_chat_human_risk_acceptance(
    root: Path,
    *,
    envelope: Mapping[str, Any],
    q4_result: Mapping[str, Any],
    current_task_commit_override: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if envelope.get("type") != SATISFACTION_MODE:
        raise ValueError("Q4 chat-human envelope has invalid type")
    decision_id = envelope.get("decision_id")
    if not isinstance(decision_id, str) or not decision_id:
        raise ValueError("Q4 chat-human envelope requires decision_id")

    task_id = q4_result.get("task")
    q4_task_commit = q4_result.get("task_commit")
    review_id = q4_result.get("review_id")
    if not all(isinstance(value, str) and value for value in (task_id, q4_task_commit, review_id)):
        raise ValueError("Q4 REVISE result is missing exact task/review identity")
    if q4_result.get("role") != "Spec-Test Contract Reviewer":
        raise ValueError("chat human risk acceptance requires the canonical Q4 reviewer")
    if q4_result.get("verdict") != "REVISE":
        raise ValueError("chat human risk acceptance may satisfy only Q4 REVISE")
    if q4_result.get("evidence_status") != "SUFFICIENT":
        raise ValueError("chat human risk acceptance requires sufficient Q4 evidence")
    if q4_result.get("confidence") not in {"HIGH", "MEDIUM"}:
        raise ValueError("chat human risk acceptance requires MEDIUM/HIGH Q4 confidence")

    role_output = q4_result.get("role_output")
    if not isinstance(role_output, Mapping):
        raise ValueError("Q4 REVISE result has invalid role_output")
    blocking = role_output.get("BLOCKING_FINDING_IDS")
    if not isinstance(blocking, list) or not blocking or not all(isinstance(item, str) and item for item in blocking):
        raise ValueError("chat human risk acceptance requires explicit blocking finding IDs")
    expected_findings = list(dict.fromkeys(blocking))

    observed_current = (
        current_task_commit_override
        if current_task_commit_override is not None
        else current_task_commit(root, task_id)
    )
    if not isinstance(observed_current, str) or not observed_current:
        raise ValueError("cannot resolve current task commit for chat human decision")
    _require_ancestor(root, q4_task_commit, observed_current)

    event = HumanDecisionStore(root).require_resolved(
        decision_id=decision_id,
        task_id=task_id,
        task_commit=observed_current,
        stage=GATE_STAGE,
        decision_type=DECISION_TYPE,
        accepted_decisions={"ACCEPT_RISK", "OVERRIDE_WITH_BACKLOG"},
    )
    request = event["request"]
    context = request.get("context")
    if not isinstance(context, Mapping):
        raise ValueError("chat human decision requires structured context")
    if context.get("q4_review_id") != review_id:
        raise ValueError("chat human decision does not bind the frozen Q4 review")
    if context.get("q4_task_commit") != q4_task_commit:
        raise ValueError("chat human decision does not bind the frozen Q4 task commit")
    accepted = context.get("accepted_finding_ids")
    if accepted != expected_findings:
        raise ValueError("chat human decision must accept every blocking Q4 finding")
    backlog = context.get("residual_backlog")
    if not isinstance(backlog, list) or not backlog or not all(isinstance(item, str) and item.strip() for item in backlog):
        raise ValueError("chat human decision must preserve non-empty residual backlog")
    if context.get("q4_verdict") != "REVISE":
        raise ValueError("chat human decision must preserve q4_verdict=REVISE")

    return {
        "satisfaction": SATISFACTION_MODE,
        "decision_id": decision_id,
        "authority": "CHAT_HUMAN_APPROVAL",
        "task_id": task_id,
        "task_commit": observed_current,
        "q4_task_commit": q4_task_commit,
        "q4_review_id": review_id,
        "q4_verdict": "REVISE",
        "accepted_finding_ids": expected_findings,
        "residual_backlog": list(backlog),
    }
