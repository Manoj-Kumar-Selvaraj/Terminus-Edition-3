"""Validate exact authenticated human risk acceptance for Q4 REVISE outcomes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from feedback.provenance import ProvenanceValidator
from feedback.registry import LearningStore
from feedback.schema_validation import LearningSchemaValidator
from retrieval.policy import RetrievalPolicy

SATISFACTION_MODE = "AUTHENTICATED_HUMAN_RISK_ACCEPTANCE"
CATEGORY = "HUMAN_RISK_ACCEPTANCE"
_GATE_STAGE = "QUALITY_INTERLOCK"
_FEEDBACK_ID_RE = re.compile(r"\bfeedback_[0-9a-f]{64}\b")


def feedback_id_from_evidence(evidence: str) -> str:
    matches = list(dict.fromkeys(_FEEDBACK_ID_RE.findall(evidence)))
    if len(matches) != 1:
        return ""
    return matches[0]


def _machine_principals(root: Path) -> set[str]:
    policy = RetrievalPolicy(root)
    principals = set(policy.role_ids)
    principals.update(str(alias) for alias in policy.role_aliases)
    return principals


def validate_human_risk_acceptance(
    root: Path,
    *,
    envelope: Mapping[str, Any],
    q4_result: Mapping[str, Any],
    store: LearningStore | None = None,
) -> dict[str, Any]:
    """Return normalized acceptance metadata or raise ValueError.

    The signed HUMAN_FEEDBACK event is the authority artifact. The stage-result
    envelope only points at the exact feedback event and cannot create authority.
    """
    root = root.resolve()
    if envelope.get("type") != SATISFACTION_MODE:
        raise ValueError("Q4 human-risk envelope has invalid type")
    feedback_id = envelope.get("feedback_id")
    if not isinstance(feedback_id, str) or not _FEEDBACK_ID_RE.fullmatch(feedback_id):
        raise ValueError("Q4 human-risk envelope requires one canonical feedback_id")

    task_id = q4_result.get("task")
    task_commit = q4_result.get("task_commit")
    review_id = q4_result.get("review_id")
    if not all(isinstance(value, str) and value for value in (task_id, task_commit, review_id)):
        raise ValueError("Q4 REVISE result is missing exact task/review identity")
    if q4_result.get("role") != "Spec-Test Contract Reviewer":
        raise ValueError("Q4 human risk acceptance requires the canonical Q4 reviewer")
    if q4_result.get("verdict") != "REVISE":
        raise ValueError("Q4 human risk acceptance may satisfy only a frozen Q4 REVISE")
    if q4_result.get("evidence_status") != "SUFFICIENT":
        raise ValueError("Q4 human risk acceptance requires sufficient frozen Q4 evidence")
    if q4_result.get("confidence") not in {"HIGH", "MEDIUM"}:
        raise ValueError("Q4 human risk acceptance requires MEDIUM/HIGH Q4 confidence")

    role_output = q4_result.get("role_output")
    if not isinstance(role_output, Mapping):
        raise ValueError("Q4 REVISE result has invalid role_output")
    blocking = role_output.get("BLOCKING_FINDING_IDS")
    if not isinstance(blocking, list) or not blocking or not all(
        isinstance(item, str) and item for item in blocking
    ):
        raise ValueError("Q4 human risk acceptance requires explicit blocking finding IDs")
    expected_findings = list(dict.fromkeys(blocking))

    learning = store or LearningStore(root)
    event = learning.feedback.get_latest("feedback_id", feedback_id)
    if event is None:
        raise ValueError("Q4 human risk acceptance feedback is unavailable")
    LearningSchemaValidator(root).validate("feedback", event)
    if not ProvenanceValidator(root).validate_feedback_event(event):
        raise ValueError("Q4 human risk acceptance feedback is not authoritative")

    source = event.get("source")
    task = event.get("task")
    observation = event.get("observation")
    provenance = event.get("provenance")
    if not all(isinstance(value, Mapping) for value in (source, task, observation, provenance)):
        raise ValueError("Q4 human risk acceptance feedback envelope is invalid")
    producer = str(source.get("producer") or "")
    if source.get("type") != "HUMAN_REVIEW" or not producer:
        raise ValueError("Q4 risk acceptance requires HUMAN_REVIEW authority")
    if producer in _machine_principals(root):
        raise ValueError("Q4 risk acceptance cannot be authored by a Terminus machine role")
    if provenance.get("trust_status") != "HUMAN_AUTHENTICATED":
        raise ValueError("Q4 risk acceptance requires HUMAN_AUTHENTICATED provenance")
    if task.get("task_id") != task_id or task.get("task_commit") != task_commit:
        raise ValueError("Q4 risk acceptance must bind the exact Q4 task commit")
    if observation.get("category") != CATEGORY:
        raise ValueError("Q4 risk acceptance feedback has the wrong category")
    if observation.get("stage_hint") != _GATE_STAGE:
        raise ValueError("Q4 risk acceptance must be scoped to QUALITY_INTERLOCK")

    detail = observation.get("value")
    if not isinstance(detail, Mapping):
        raise ValueError("Q4 risk acceptance requires structured observation.value")
    if detail.get("decision") != "ACCEPTED":
        raise ValueError("Q4 risk acceptance decision must be ACCEPTED")
    if detail.get("q4_verdict") != "REVISE":
        raise ValueError("Q4 risk acceptance must preserve q4_verdict=REVISE")
    if detail.get("q4_review_id") != review_id:
        raise ValueError("Q4 risk acceptance does not bind the frozen Q4 review")
    accepted = detail.get("accepted_finding_ids")
    if accepted != expected_findings:
        raise ValueError("Q4 risk acceptance must explicitly accept every blocking Q4 finding")
    backlog = detail.get("residual_backlog")
    if not isinstance(backlog, list) or not backlog or not all(
        isinstance(item, str) and item.strip() for item in backlog
    ):
        raise ValueError("Q4 risk acceptance must retain non-empty residual_backlog")

    return {
        "satisfaction": SATISFACTION_MODE,
        "feedback_id": feedback_id,
        "principal": f"human:{producer}",
        "task_id": task_id,
        "task_commit": task_commit,
        "q4_review_id": review_id,
        "q4_verdict": "REVISE",
        "accepted_finding_ids": expected_findings,
        "residual_backlog": list(backlog),
    }
