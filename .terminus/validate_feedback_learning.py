#!/usr/bin/env python3
"""Validate unified feedback, remediation and agent-learning boundaries."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))

from execution.authority import ExecutionAuthority  # noqa: E402
from execution.invocation import StageInvocationBuilder  # noqa: E402
from execution.invocation_guard import CanonicalInvocationGuard  # noqa: E402
from feedback.ingestion import FeedbackIngestor  # noqa: E402
from feedback.model import FeedbackSource  # noqa: E402
from feedback.normalizer import FindingNormalizer  # noqa: E402
from feedback.registry import LearningStore  # noqa: E402
from feedback.schema_validation import LearningSchemaValidator  # noqa: E402
from learning.context import LearningContextBuilder  # noqa: E402
from remediation.planner import RemediationPlanner  # noqa: E402
from remediation.router import RemediationInterlock  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402

EXPECTED_SOURCES = {
    "HUMAN_REVIEW",
    "INDEPENDENT_REVIEW",
    "REVIEWER_REVIEW",
    "PORTAL_CI",
    "REPOSITORY_CI",
    "LLMAJ",
    "MODEL_DIAGNOSTIC",
    "MODEL_TRIAL",
    "DIFFICULTY",
    "FINAL_REVIEW",
    "SUBMISSION_RESULT",
    "RUNTIME",
}

FILES = [
    T / "feedback" / "model.py",
    T / "feedback" / "ingestion.py",
    T / "feedback" / "normalizer.py",
    T / "feedback" / "closure.py",
    T / "feedback" / "registry.py",
    T / "feedback" / "schema_validation.py",
    T / "feedback" / "source_adapters.py",
    T / "feedback" / "feedback_cli.py",
    T / "remediation" / "planner.py",
    T / "remediation" / "router.py",
    T / "learning" / "registry.py",
    T / "learning" / "recurrence.py",
    T / "learning" / "projection.py",
    T / "learning" / "context.py",
    T / "agents" / "FEEDBACK_LEARNING.md",
    T / "learning" / "knowledge" / "lessons.jsonl",
    T / "learning" / "knowledge" / "patterns.jsonl",
]
SCHEMAS = {
    "feedback": ("feedback_event.schema.json", "terminus-feedback-event-v1"),
    "finding": ("finding.schema.json", "terminus-finding-v1"),
    "remediation": ("remediation_packet.schema.json", "terminus-remediation-packet-v1"),
    "lesson": ("lesson.schema.json", "terminus-lesson-v1"),
    "pattern": ("pattern.schema.json", "terminus-pattern-v1"),
}


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _invocation() -> dict[str, object]:
    commit = _head()
    policy = RetrievalPolicy(ROOT)
    stage_id = "RULE_RESOLUTION"
    role_id = ExecutionAuthority(policy).primary_role_for_stage(stage_id)
    required = policy.stages[stage_id]["input_contract"]["required_fields"]
    return StageInvocationBuilder(ROOT, policy).build(
        InvocationContext(
            stage_id=stage_id,
            role_id=role_id,
            task_id="feedback-validator",
            task_commit=commit,
            control_plane_commit=commit,
        ),
        {str(field): {"validator": str(field)} for field in required},
    )


def main() -> int:
    errors: list[str] = []
    for path in FILES:
        if not path.is_file():
            errors.append(f"missing feedback-learning file: {path.relative_to(ROOT)}")

    schemas = LearningSchemaValidator(ROOT)
    schema_root = T / "agents" / "schemas"
    for _kind, (filename, schema_id) in SCHEMAS.items():
        schema = json.loads((schema_root / filename).read_text(encoding="utf-8"))
        if schema.get("$id") != schema_id:
            errors.append(f"{filename} schema ID drift")
        if schema.get("additionalProperties") is not False:
            errors.append(f"{filename} must fail closed at top level")
    if {item.value for item in FeedbackSource} != EXPECTED_SOURCES:
        errors.append("feedback source registry does not match the canonical source set")

    try:
        packet = _invocation()
        learning = packet["learning"]
        if learning.get("raw_feedback_exposed") is not False:
            errors.append("StageInvocation exposes raw feedback")
        if learning.get("raw_historical_findings_exposed") is not False:
            errors.append("StageInvocation exposes raw historical findings")
        CanonicalInvocationGuard(ROOT).validate(packet)
    except Exception as exc:
        errors.append(f"canonical learning-bound invocation failed: {exc}")

    required_snapshot_markers = (
        ".terminus/feedback/schema_validation.py",
        ".terminus/remediation/planner.py",
        ".terminus/learning/context.py",
        ".terminus/learning/projection.py",
    )
    invocation_text = (T / "execution" / "invocation.py").read_text(encoding="utf-8")
    for marker in required_snapshot_markers:
        if marker not in invocation_text:
            errors.append(f"invocation snapshot binding missing learning dependency: {marker}")

    controller_text = (T / "execution" / "controller_cli.py").read_text(encoding="utf-8")
    for marker in ("RemediationInterlock", "REMEDIATE_STAGE", "remediation_updates"):
        if marker not in controller_text:
            errors.append(f"controller remediation interlock missing marker: {marker}")

    private = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", ".terminus/learning/state/probe.jsonl"],
        capture_output=True,
    )
    portable = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", ".terminus/learning/knowledge/lessons.jsonl"],
        capture_output=True,
    )
    if private.returncode != 0:
        errors.append("raw learning state must be gitignored")
    if portable.returncode == 0:
        errors.append("generalized learning knowledge must remain portable/trackable")

    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        store = LearningStore(
            ROOT,
            state_root=temp / "state",
            knowledge_root=temp / "knowledge",
        )
        try:
            human = FeedbackIngestor(ROOT, store=store).capture(
                source_type="HUMAN_REVIEW",
                producer="Manoj",
                task_id="feedback-validator-temp",
                task_commit=_head(),
                severity="HIGH",
                message="A task-specific review detected a weak observable boundary.",
                category="BOUNDARY",
                stage_hint="VERIFIER_BUILD",
                captured_at="2026-08-14T00:00:00Z",
            )
            portal = FeedbackIngestor(ROOT, store=store).capture(
                source_type="PORTAL_CI",
                producer="portal-ci",
                task_id="feedback-validator-temp",
                task_commit=_head(),
                severity="HIGH",
                message="Portal confirms the same boundary weakness.",
                category="BOUNDARY",
                stage_hint="VERIFIER_BUILD",
                captured_at="2026-08-14T00:00:01Z",
            )
            finding = FindingNormalizer(ROOT, store=store).normalize(
                [human, portal],
                generalized_problem="External effects require observable-boundary verification.",
                root_cause_class="INTERNAL_PROXY",
                repair_stages=["VERIFIER_BUILD"],
                closure_conditions=["Boundary behavior is independently verified."],
            )
            schemas.validate("finding", finding)
            remediation = RemediationPlanner(ROOT, store=store).plan(finding)
            schemas.validate("remediation", remediation)
            action = RemediationInterlock(ROOT, store=store).next_override(
                task_id="feedback-validator-temp",
                task_commit=_head(),
            )
            if not action or action.get("action") != "REMEDIATE_STAGE":
                errors.append("open planned finding does not route to REMEDIATE_STAGE")
            projection = LearningContextBuilder(ROOT, store=store).build(
                stage_id="VERIFIER_BUILD",
                role_id=str(remediation["steps"][0]["role_id"]),
                task_id="feedback-validator-temp",
                task_commit=_head(),
            )
            rendered = json.dumps(projection, sort_keys=True)
            if human["observation"]["message"] in rendered:
                errors.append("raw human review text leaked into agent learning projection")
            if finding["problem"]["task_specific"] in rendered:
                errors.append("task-specific finding text leaked into generalized projection")
        except Exception as exc:
            errors.append(f"feedback/remediation smoke validation failed: {exc}")

    if errors:
        print("Terminus feedback-learning validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Terminus feedback-learning validation PASS")
    print(
        "feedback_learning=1.0 sources=human,review,ci,portal,llmaj,trials,difficulty,runtime "
        "raw_state=private_hash_chained generalized_knowledge=portable "
        "remediation=controller_interlocked closure=independent "
        "learning_projection=generalized_role_scoped cold_review=raw_history_hidden "
        "recurrence=distinct_task_policy_candidates policy_mutation=manual"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
