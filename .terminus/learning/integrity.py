"""Replay semantic authority before terminal findings or learned artifacts are consumed."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

from authority.receipts import AuthorityReceiptValidator
from execution.authority import ExecutionAuthority
from retrieval.policy import RetrievalPolicy

from feedback.model import lesson_identity, pattern_identity
from feedback.registry import LearningStore
from feedback.schema_validation import LearningSchemaValidator


class LearningIntegrityValidator:
    """Treat registries as persistence, never as semantic authority."""

    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)
        self.policy = RetrievalPolicy(self.root)
        self.authority = ExecutionAuthority(self.policy)
        self.semantic_authority = AuthorityReceiptValidator(self.root)

    def validate_terminal_finding(self, finding: Mapping[str, Any]) -> None:
        self.schemas.validate("finding", finding)
        closure = self._closure()
        state = str(finding.get("state"))
        if state == "REPAIRED":
            closure.assert_repaired_authorized(finding)
        elif state in {"VERIFIED", "CLOSED"}:
            closure.assert_learning_eligible(finding)
        elif state == "WONT_FIX":
            closure.assert_conflict_resolved(finding)

    @staticmethod
    def lesson_activation_claim(lesson: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "lesson_id": lesson.get("lesson_id"),
            "state": "ACTIVE",
            "category": lesson.get("category"),
            "failure_pattern": lesson.get("failure_pattern"),
            "root_cause_class": lesson.get("root_cause_class"),
            "future_rule": lesson.get("future_rule"),
            "targets": copy.deepcopy(lesson.get("targets")),
            "sources": sorted(str(item) for item in lesson.get("sources", [])),
            "promotion": copy.deepcopy(lesson.get("promotion")),
        }

    def validate_lesson(self, lesson: Mapping[str, Any]) -> None:
        self.schemas.validate("lesson", lesson)
        if lesson_identity(lesson) != lesson.get("lesson_id"):
            raise ValueError("lesson_id does not match canonical lesson identity")
        targets = lesson.get("targets")
        if not isinstance(targets, Mapping):
            raise ValueError("lesson targets are invalid")
        stages = targets.get("stages")
        roles = targets.get("roles")
        if not isinstance(stages, list) or not stages:
            raise ValueError("lesson must target at least one explicit stage")
        if not isinstance(roles, list) or not roles:
            raise ValueError("lesson must target at least one explicit role")
        for stage_id in stages:
            if stage_id not in self.policy.stages:
                raise ValueError(f"lesson targets unknown stage: {stage_id}")
        canonical_roles = {
            self.authority.primary_role_for_stage(stage_id) for stage_id in stages
        }
        if not canonical_roles.intersection(str(role) for role in roles):
            raise ValueError(
                "lesson role targets do not include an owner for any target stage"
            )

        sources = [str(item) for item in lesson.get("sources", [])]
        if not sources:
            raise ValueError("lesson requires source findings")
        findings: list[dict[str, Any]] = []
        closure = self._closure()
        for source in sources:
            finding = self.store.findings.get_latest("finding_id", source)
            if finding is None:
                raise ValueError(f"lesson source finding is unavailable: {source}")
            closure.assert_learning_eligible(finding)
            if finding.get("category") != lesson.get("category"):
                raise ValueError("lesson category does not match every source finding")
            problem = finding.get("problem")
            if not isinstance(problem, Mapping):
                raise ValueError("lesson source finding problem is invalid")
            if problem.get("generalized") != lesson.get("failure_pattern"):
                raise ValueError(
                    "lesson failure_pattern is not derived from every source finding"
                )
            if problem.get("root_cause_class") != lesson.get("root_cause_class"):
                raise ValueError(
                    "lesson root_cause_class does not match every source finding"
                )
            findings.append(finding)
        distinct_tasks = len({str(item["task_id"]) for item in findings})
        expected_promotion = {
            "occurrences": len(sources),
            "distinct_tasks": distinct_tasks,
            "policy_candidate": distinct_tasks >= 3,
        }
        if lesson.get("promotion") != expected_promotion:
            raise ValueError(
                "lesson promotion does not match independently verified source findings"
            )
        if lesson.get("state") == "ACTIVE":
            receipt = lesson.get("authority_receipt")
            self.semantic_authority.verify(
                receipt if isinstance(receipt, Mapping) else None,
                action="LESSON_ACTIVATION",
                principal="learning-curator",
                claim=self.lesson_activation_claim(lesson),
            )

    def validate_pattern(self, pattern: Mapping[str, Any]) -> None:
        self.schemas.validate("pattern", pattern)
        if pattern_identity(pattern) != pattern.get("pattern_id"):
            raise ValueError("pattern_id does not match canonical pattern identity")
        finding_ids = [str(item) for item in pattern.get("finding_ids", [])]
        if len(finding_ids) < 2:
            raise ValueError("recurrence pattern requires at least two findings")
        findings: list[dict[str, Any]] = []
        closure = self._closure()
        for finding_id in finding_ids:
            finding = self.store.findings.get_latest("finding_id", finding_id)
            if finding is None:
                raise ValueError(
                    f"pattern source finding is unavailable: {finding_id}"
                )
            closure.assert_learning_eligible(finding)
            if finding.get("category") != pattern.get("category"):
                raise ValueError("pattern category does not match source finding")
            problem = finding.get("problem")
            if not isinstance(problem, Mapping) or problem.get(
                "root_cause_class"
            ) != pattern.get("root_cause_class"):
                raise ValueError("pattern root_cause_class does not match source finding")
            findings.append(finding)
        task_ids = sorted({str(item["task_id"]) for item in findings})
        if list(pattern.get("task_ids", [])) != task_ids:
            raise ValueError("pattern task_ids do not match source findings")
        if int(pattern.get("occurrences", 0)) != len(finding_ids):
            raise ValueError("pattern occurrences do not match source findings")
        should_promote = len(task_ids) >= 3
        if bool(pattern.get("policy_candidate")) != should_promote:
            raise ValueError(
                "pattern policy_candidate does not match distinct-task threshold"
            )
        expected_status = "POLICY_CANDIDATE" if should_promote else "ACTIVE"
        if pattern.get("status") != expected_status:
            raise ValueError("pattern status does not match policy-candidate state")

        lessons = {
            str(item["lesson_id"]): item
            for item in self.store.lessons.latest_by("lesson_id")
        }
        expected_lesson_ids: set[str] = set()
        finding_set = set(finding_ids)
        for lesson_id, lesson in lessons.items():
            lesson_sources = {str(item) for item in lesson.get("sources", [])}
            if not lesson_sources.intersection(finding_set):
                continue
            self.validate_lesson(lesson)
            expected_lesson_ids.add(lesson_id)
        if list(pattern.get("lesson_ids", [])) != sorted(expected_lesson_ids):
            raise ValueError(
                "pattern lesson_ids do not match validated lessons for its findings"
            )

    def _closure(self):
        from feedback.closure import FindingClosure

        return FindingClosure(self.root, store=self.store)
