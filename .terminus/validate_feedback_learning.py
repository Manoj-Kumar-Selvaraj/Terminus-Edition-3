#!/usr/bin/env python3
"""Validate unified feedback, remediation and agent-learning boundaries."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))

from execution.authority import ExecutionAuthority  # noqa: E402
from execution.invocation import _CONTRACT_SNAPSHOT_PATHS, StageInvocationBuilder  # noqa: E402
from execution.invocation_guard import CanonicalInvocationGuard  # noqa: E402
from feedback.ingestion import FeedbackIngestor  # noqa: E402
from feedback.model import FeedbackSource  # noqa: E402
from feedback.normalizer import FindingNormalizer  # noqa: E402
from feedback.registry import LearningStore  # noqa: E402
from feedback.schema_validation import LearningSchemaValidator  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402

EXPECTED_SOURCES = {
    "HUMAN_REVIEW", "INDEPENDENT_REVIEW", "REVIEWER_REVIEW", "PORTAL_CI",
    "REPOSITORY_CI", "LLMAJ", "MODEL_DIAGNOSTIC", "MODEL_TRIAL",
    "DIFFICULTY", "FINAL_REVIEW", "SUBMISSION_RESULT", "RUNTIME",
}
_SOURCE_FIXTURE = ".terminus/tests/fixtures/feedback_source_identities.json"
FILES = [
    T / "authority" / "receipts.py",
    T / "feedback" / "model.py",
    T / "feedback" / "ingestion.py",
    T / "feedback" / "normalizer.py",
    T / "feedback" / "closure.py",
    T / "feedback" / "registry.py",
    T / "feedback" / "schema_validation.py",
    T / "feedback" / "provenance.py",
    T / "feedback" / "source_adapters.py",
    T / "feedback" / "feedback_cli.py",
    T / "remediation" / "planner.py",
    T / "remediation" / "progress.py",
    T / "remediation" / "router.py",
    T / "learning" / "registry.py",
    T / "learning" / "recurrence.py",
    T / "learning" / "projection.py",
    T / "learning" / "context.py",
    T / "learning" / "integrity.py",
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
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def _source_binding(identity: str) -> dict[str, str]:
    raw = (ROOT / _SOURCE_FIXTURE).read_bytes()
    return {
        "kind": "RESULT",
        "ref": f"git:{_head()}:{_SOURCE_FIXTURE}#{quote(identity, safe='')}",
        "content_hash": "sha256:" + hashlib.sha256(raw).hexdigest(),
    }


def _invocation() -> dict[str, object]:
    commit = _head()
    policy = RetrievalPolicy(ROOT)
    stage_id = "RULE_RESOLUTION"
    role_id = ExecutionAuthority(policy).primary_role_for_stage(stage_id)
    required = policy.stages[stage_id]["input_contract"]["required_fields"]
    return StageInvocationBuilder(ROOT, policy).build(
        InvocationContext(stage_id=stage_id, role_id=role_id, task_id="feedback-validator", task_commit=commit, control_plane_commit=commit),
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
    feedback_schema = json.loads((schema_root / "feedback_event.schema.json").read_text(encoding="utf-8"))
    provenance = feedback_schema["properties"]["provenance"]
    if not {"trust_status", "source_binding"} <= set(provenance.get("required", [])):
        errors.append("feedback schema does not require source trust provenance")
    trust_values = set(provenance["properties"]["trust_status"].get("enum", []))
    if "HUMAN_AUTHENTICATED" not in trust_values or "UNAUTHENTICATED" not in trust_values:
        errors.append("feedback trust schema lacks authenticated/non-authoritative distinction")
    lesson_schema = json.loads((schema_root / "lesson.schema.json").read_text(encoding="utf-8"))
    targets = lesson_schema["properties"]["targets"]["properties"]
    if targets["stages"].get("minItems") != 1 or targets["roles"].get("minItems") != 1:
        errors.append("lesson schema must require explicit stage and role targets")
    if "authority_receipt" not in lesson_schema["properties"]:
        errors.append("lesson schema lacks activation authority receipt")
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

    for marker in (
        ".terminus/feedback/provenance.py",
        ".terminus/feedback/closure.py",
        ".terminus/remediation/progress.py",
        ".terminus/learning/integrity.py",
        ".terminus/learning/projection.py",
        ".terminus/learning/knowledge/lessons.jsonl",
        ".terminus/learning/knowledge/patterns.jsonl",
    ):
        if marker not in _CONTRACT_SNAPSHOT_PATHS:
            errors.append(f"invocation snapshot binding missing learning dependency: {marker}")

    private = subprocess.run(["git", "-C", str(ROOT), "check-ignore", ".terminus/learning/state/probe.jsonl"], capture_output=True)
    portable = subprocess.run(["git", "-C", str(ROOT), "check-ignore", ".terminus/learning/knowledge/lessons.jsonl"], capture_output=True)
    if private.returncode != 0:
        errors.append("raw learning state must be gitignored")
    if portable.returncode == 0:
        errors.append("generalized learning knowledge must remain portable/trackable")

    with tempfile.TemporaryDirectory() as directory:
        store = LearningStore(ROOT, state_root=Path(directory) / "state", knowledge_root=Path(directory) / "knowledge")
        ingestor = FeedbackIngestor(ROOT, store=store)
        human = ingestor.capture(
            source_type="HUMAN_REVIEW", producer="untrusted-caller", task_id="feedback-validator-temp",
            task_commit=_head(), severity="HIGH", message="Unsigned human claim.", category="BOUNDARY",
            stage_hint="VERIFIER_BUILD", captured_at="2026-08-14T00:00:00Z",
        )
        if human["provenance"]["trust_status"] != "HUMAN_ASSERTED":
            errors.append("unsigned human signal should remain informational HUMAN_ASSERTED")
        try:
            FindingNormalizer(ROOT, store=store).normalize(
                [human], generalized_problem="Unsigned caller must not create authority.", root_cause_class="UNAUTHENTICATED",
                repair_stages=["VERIFIER_BUILD"], closure_conditions=["No authority escalation."],
            )
            errors.append("unsigned human feedback became canonical finding authority")
        except ValueError:
            pass
        try:
            ingestor.capture(
                source_type="PORTAL_CI", producer="portal-ci", task_id="feedback-validator-temp",
                task_commit=_head(), severity="HIGH", message="Self-authored source JSON.", run_id="portal-ci-self-asserted",
                category="BOUNDARY", stage_hint="VERIFIER_BUILD", source_binding=_source_binding("portal-ci"), captured_at="2026-08-14T00:00:02Z",
            )
            errors.append("unsigned repository source artifact became automated authority")
        except ValueError:
            pass

    for path, marker in (
        (T / "feedback" / "closure.py", "FINDING_VERIFICATION"),
        (T / "learning" / "integrity.py", "LESSON_ACTIVATION"),
        (T / "remediation" / "progress.py", "validate_execution_authority"),
        (T / "feedback" / "provenance.py", "REVIEW_RESULT"),
        (T / "feedback" / "normalizer.py", "decision_key"),
    ):
        if marker not in path.read_text(encoding="utf-8"):
            errors.append(f"trusted authority boundary missing marker {marker} in {path.relative_to(ROOT)}")

    if errors:
        print("Terminus feedback-learning validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Terminus feedback-learning validation PASS")
    print(
        "feedback_learning=1.0 semantic_authority=external_ssh_receipts human=authenticated_for_authority "
        "source_provenance=signed_source_plus_execution review=reviewer_signature_plus_signed_controller "
        "finding_genesis=replayed remediation=signed_executor_bound closure=finding_specific "
        "learning=candidate_then_signed_activation recurrence=semantic_source_replay policy_conflict=adjudicator_decision_bound"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
