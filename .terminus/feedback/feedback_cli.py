#!/usr/bin/env python3
"""CLI for feedback ingestion, remediation, closure and agent learning."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from feedback.closure import FindingClosure  # noqa: E402
from feedback.ingestion import FeedbackIngestor  # noqa: E402
from feedback.model import FeedbackSource, Severity  # noqa: E402
from feedback.normalizer import FindingNormalizer  # noqa: E402
from feedback.registry import LearningStore  # noqa: E402
from learning.context import LearningContextBuilder  # noqa: E402
from learning.integrity import LearningIntegrityValidator  # noqa: E402
from learning.recurrence import RecurrenceAnalyzer  # noqa: E402
from learning.registry import LessonRegistry  # noqa: E402
from remediation.planner import RemediationPlanner  # noqa: E402


def _json_arg(value: str | None) -> Any:
    return None if value is None else json.loads(value)


def _emit(value: Any) -> int:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def _event(store: LearningStore, feedback_id: str) -> dict[str, Any]:
    event = store.feedback.get_latest("feedback_id", feedback_id)
    if event is None:
        raise ValueError(f"unknown feedback_id: {feedback_id}")
    return event


def _finding(store: LearningStore, finding_id: str) -> dict[str, Any]:
    finding = store.findings.get_latest("finding_id", finding_id)
    if finding is None:
        raise ValueError(f"unknown finding_id: {finding_id}")
    return finding


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="capture one immutable feedback event")
    add.add_argument("--source", required=True, choices=[item.value for item in FeedbackSource])
    add.add_argument("--producer", required=True)
    add.add_argument("--task-id", required=True)
    add.add_argument("--task-commit", required=True)
    add.add_argument("--severity", default="MEDIUM", choices=[item.value for item in Severity])
    add.add_argument("--message", required=True)
    add.add_argument("--category")
    add.add_argument("--stage-hint")
    add.add_argument("--role-hint")
    add.add_argument("--run-id")
    add.add_argument("--external-ref")
    add.add_argument("--source-binding-json")
    add.add_argument("--authority-receipt-json")
    add.add_argument("--test-id")
    add.add_argument("--metric")
    add.add_argument("--value-json")
    add.add_argument("--expected-json")
    add.add_argument("--evidence-json")
    add.add_argument("--captured-at")

    normalize = sub.add_parser("normalize", help="normalize authenticated feedback into one canonical finding")
    normalize.add_argument("--feedback-id", action="append", required=True)
    normalize.add_argument("--generalized", required=True)
    normalize.add_argument("--root-cause", required=True)
    normalize.add_argument("--repair-stage", action="append", default=[])
    normalize.add_argument("--caught-by", action="append", default=[])
    normalize.add_argument("--closure", action="append", default=[])
    normalize.add_argument("--verification-owner", default="CI_ORCHESTRATOR")

    plan = sub.add_parser("plan", help="create a controlled remediation packet")
    plan.add_argument("--finding-id", required=True)

    repaired = sub.add_parser("mark-repaired")
    repaired.add_argument("--finding-id", required=True)
    repaired.add_argument("--remediation-id", required=True)
    repaired.add_argument("--task-commit", required=True)

    resolve_conflict = sub.add_parser("resolve-conflict")
    resolve_conflict.add_argument("--finding-id", required=True)
    resolve_conflict.add_argument("--feedback-id", action="append", required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--finding-id", required=True)
    verify.add_argument("--verifier-role", required=True)
    verify.add_argument("--feedback-id", action="append", required=True)
    verify.add_argument("--verified-only", action="store_true")

    learn = sub.add_parser("learn", help="create a lesson candidate; activation requires signed curator authority")
    learn.add_argument("--finding-id", required=True)
    learn.add_argument("--future-rule", required=True)
    learn.add_argument("--extra-stage", action="append", default=[])
    learn.add_argument("--extra-role", action="append", default=[])
    learn.add_argument("--domain", action="append", default=[])
    learn.add_argument("--activate", action="store_true")
    learn.add_argument("--authority-receipt-json")

    analyze = sub.add_parser("analyze")
    analyze.add_argument("--policy-threshold", type=int, default=3)

    project = sub.add_parser("project")
    project.add_argument("--stage-id", required=True)
    project.add_argument("--role-id", required=True)
    project.add_argument("--task-id")
    project.add_argument("--task-commit")

    sub.add_parser("status")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = LearningStore(ROOT)
    if args.command == "add":
        evidence = _json_arg(args.evidence_json)
        if evidence is not None and not isinstance(evidence, list):
            raise ValueError("--evidence-json must decode to an array")
        source_binding = _json_arg(args.source_binding_json)
        receipt = _json_arg(args.authority_receipt_json)
        for label, value in (("--source-binding-json", source_binding), ("--authority-receipt-json", receipt)):
            if value is not None and not isinstance(value, dict):
                raise ValueError(f"{label} must decode to an object")
        return _emit(
            FeedbackIngestor(ROOT, store=store).capture(
                source_type=args.source,
                producer=args.producer,
                task_id=args.task_id,
                task_commit=args.task_commit,
                severity=args.severity,
                message=args.message,
                category=args.category,
                stage_hint=args.stage_hint,
                role_hint=args.role_hint,
                run_id=args.run_id,
                external_ref=args.external_ref,
                source_binding=source_binding,
                authority_receipt=receipt,
                test_id=args.test_id,
                metric=args.metric,
                value=_json_arg(args.value_json),
                expected=_json_arg(args.expected_json),
                evidence=evidence,
                captured_at=args.captured_at,
            )
        )
    if args.command == "normalize":
        return _emit(
            FindingNormalizer(ROOT, store=store).normalize(
                [_event(store, feedback_id) for feedback_id in args.feedback_id],
                generalized_problem=args.generalized,
                root_cause_class=args.root_cause,
                repair_stages=args.repair_stage or None,
                should_have_been_caught_by=args.caught_by,
                closure_conditions=args.closure or None,
                verification_owner=args.verification_owner,
            )
        )
    if args.command == "plan":
        return _emit(RemediationPlanner(ROOT, store=store).plan(_finding(store, args.finding_id)))
    if args.command == "mark-repaired":
        return _emit(FindingClosure(ROOT, store=store).mark_repaired(args.finding_id, args.task_commit, remediation_id=args.remediation_id))
    if args.command == "resolve-conflict":
        return _emit(FindingClosure(ROOT, store=store).resolve_conflict(args.finding_id, resolution_feedback=[_event(store, value) for value in args.feedback_id]))
    if args.command == "verify":
        return _emit(FindingClosure(ROOT, store=store).verify(args.finding_id, verifier_role=args.verifier_role, verification_feedback=[_event(store, value) for value in args.feedback_id], close=not args.verified_only))
    if args.command == "learn":
        receipt = _json_arg(args.authority_receipt_json)
        if receipt is not None and not isinstance(receipt, dict):
            raise ValueError("--authority-receipt-json must decode to an object")
        return _emit(LessonRegistry(ROOT, store=store).from_finding(_finding(store, args.finding_id), future_rule=args.future_rule, extra_stages=args.extra_stage, extra_roles=args.extra_role, domains=args.domain, activate=args.activate, authority_receipt=receipt))
    if args.command == "analyze":
        return _emit(RecurrenceAnalyzer(ROOT, store=store).analyze(policy_candidate_distinct_tasks=args.policy_threshold))
    if args.command == "project":
        return _emit(LearningContextBuilder(ROOT, store=store).build(stage_id=args.stage_id, role_id=args.role_id, task_id=args.task_id, task_commit=args.task_commit))
    if args.command == "status":
        findings = store.findings.latest_by("finding_id")
        lessons = store.lessons.latest_by("lesson_id")
        patterns = store.patterns.latest_by("pattern_id")
        integrity = LearningIntegrityValidator(ROOT, store=store)
        active_lessons = []
        for lesson in lessons:
            if lesson.get("state") == "ACTIVE":
                integrity.validate_lesson(lesson)
                active_lessons.append(lesson)
        trusted_patterns = []
        for pattern in patterns:
            integrity.validate_pattern(pattern)
            trusted_patterns.append(pattern)
        return _emit({"registry_heads": store.heads(), "feedback_events": len(store.feedback.read()), "findings": len(findings), "finding_states": _counts(findings, "state"), "lessons": len(lessons), "active_lessons": len(active_lessons), "lesson_states": _counts(lessons, "state"), "patterns": len(trusted_patterns), "policy_candidates": sum(1 for pattern in trusted_patterns if pattern.get("policy_candidate") is True)})
    raise AssertionError(args.command)


def _counts(values: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value.get(field, "UNKNOWN"))
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
