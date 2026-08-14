"""Detect repeated failure patterns across tasks without auto-promoting policy."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from feedback.closure import FindingClosure
from feedback.model import pattern_identity
from feedback.registry import LearningStore
from feedback.schema_validation import LearningSchemaValidator


class RecurrenceAnalyzer:
    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)
        self.closure = FindingClosure(self.root, store=self.store)

    def analyze(self, *, policy_candidate_distinct_tasks: int = 3) -> list[dict[str, Any]]:
        if policy_candidate_distinct_tasks < 2:
            raise ValueError("policy candidate threshold must be at least two distinct tasks")
        findings = [
            finding
            for finding in self.store.findings.latest_by("finding_id")
            if finding.get("state") in {"VERIFIED", "CLOSED"}
        ]
        for finding in findings:
            self.closure.assert_learning_eligible(finding)
        lessons = self.store.lessons.latest_by("lesson_id")
        lesson_by_source: dict[str, list[str]] = defaultdict(list)
        for lesson in lessons:
            for source in lesson.get("sources", []):
                lesson_by_source[str(source)].append(str(lesson["lesson_id"]))
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for finding in findings:
            grouped[
                (str(finding["category"]), str(finding["problem"]["root_cause_class"]))
            ].append(finding)

        existing = {
            pattern["pattern_id"]: pattern
            for pattern in self.store.patterns.latest_by("pattern_id")
        }
        patterns: list[dict[str, Any]] = []
        for (category, root_cause), values in sorted(grouped.items()):
            if len(values) < 2:
                continue
            task_ids = sorted({str(item["task_id"]) for item in values})
            finding_ids = sorted(str(item["finding_id"]) for item in values)
            lesson_ids = sorted(
                {
                    lesson_id
                    for finding_id in finding_ids
                    for lesson_id in lesson_by_source.get(finding_id, [])
                }
            )
            policy_candidate = len(task_ids) >= policy_candidate_distinct_tasks
            pattern: dict[str, Any] = {
                "schema_version": "1.0",
                "category": category,
                "root_cause_class": root_cause,
                "lesson_ids": lesson_ids,
                "finding_ids": finding_ids,
                "task_ids": task_ids,
                "occurrences": len(values),
                "policy_candidate": policy_candidate,
                "status": "POLICY_CANDIDATE" if policy_candidate else "ACTIVE",
            }
            pattern["pattern_id"] = pattern_identity(pattern)
            self.schemas.validate("pattern", pattern)
            if existing.get(pattern["pattern_id"]) != pattern:
                self.store.patterns.append(pattern)
            patterns.append(pattern)
        return patterns
