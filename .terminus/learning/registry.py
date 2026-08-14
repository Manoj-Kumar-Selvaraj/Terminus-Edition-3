"""Extract reusable lessons from independently verified task findings."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Iterable, Mapping

from execution.authority import ExecutionAuthority
from retrieval.policy import RetrievalPolicy

from feedback.model import LessonState, lesson_identity
from feedback.registry import LearningStore
from feedback.schema_validation import LearningSchemaValidator


class LessonRegistry:
    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)
        self.policy = RetrievalPolicy(self.root)
        self.authority = ExecutionAuthority(self.policy)

    def from_finding(
        self,
        finding: Mapping[str, Any],
        *,
        future_rule: str,
        extra_stages: Iterable[str] = (),
        extra_roles: Iterable[str] = (),
        domains: Iterable[str] = (),
        activate: bool = True,
    ) -> dict[str, Any]:
        self.schemas.validate("finding", finding)
        if finding["state"] not in {"VERIFIED", "CLOSED"}:
            raise ValueError("only independently verified/closed findings can become lessons")
        if not future_rule.strip():
            raise ValueError("future_rule is required")
        stages = self._unique(
            list(finding["ownership"]["repair_stages"])
            + list(finding["ownership"].get("should_have_been_caught_by", []))
            + list(extra_stages)
        )
        for stage_id in stages:
            if stage_id not in self.policy.stages:
                raise ValueError(f"unknown lesson target stage: {stage_id}")
        roles = self._unique(
            list(finding["ownership"]["repair_roles"])
            + [self.authority.primary_role_for_stage(stage) for stage in stages]
            + list(extra_roles)
        )
        lesson: dict[str, Any] = {
            "schema_version": "1.0",
            "state": LessonState.ACTIVE.value if activate else LessonState.CANDIDATE.value,
            "category": finding["category"],
            "failure_pattern": finding["problem"]["generalized"],
            "root_cause_class": finding["problem"]["root_cause_class"],
            "future_rule": future_rule.strip(),
            "targets": {
                "stages": stages,
                "roles": roles,
                "domains": self._unique(domains),
            },
            "sources": [finding["finding_id"]],
            "promotion": {
                "occurrences": 1,
                "distinct_tasks": 1,
                "policy_candidate": False,
            },
        }
        lesson["lesson_id"] = lesson_identity(lesson)
        existing = self.store.lessons.get_latest("lesson_id", lesson["lesson_id"])
        if existing is not None:
            self.schemas.validate("lesson", existing)
            merged = copy.deepcopy(existing)
            merged["sources"] = self._unique(
                list(existing["sources"]) + [finding["finding_id"]]
            )
            merged["promotion"] = self._promotion(merged["sources"], existing)
            if activate:
                merged["state"] = LessonState.ACTIVE.value
            lesson = merged
        self.schemas.validate("lesson", lesson)
        if existing != lesson:
            self.store.lessons.append(lesson)
        return lesson

    def set_state(self, lesson_id: str, state: LessonState | str) -> dict[str, Any]:
        lesson = self.store.lessons.get_latest("lesson_id", lesson_id)
        if lesson is None:
            raise ValueError(f"unknown lesson_id: {lesson_id}")
        updated = copy.deepcopy(lesson)
        updated["state"] = LessonState(state).value
        if lesson_identity(updated) != lesson_id:
            raise ValueError("lesson semantic identity changed during state transition")
        self.schemas.validate("lesson", updated)
        if updated != lesson:
            self.store.lessons.append(updated)
        return updated

    def active(self, *, chain_head: str | None = None) -> list[dict[str, Any]]:
        return [
            row
            for row in self.store.lessons.latest_by("lesson_id", chain_head=chain_head)
            if row.get("state") == "ACTIVE"
        ]

    def _promotion(
        self, sources: list[str], existing: Mapping[str, Any]
    ) -> dict[str, Any]:
        findings = {
            item["finding_id"]: item
            for item in self.store.findings.latest_by("finding_id")
        }
        task_ids = {
            findings[source]["task_id"] for source in sources if source in findings
        }
        previous = existing.get("promotion", {})
        occurrences = max(len(sources), int(previous.get("occurrences", 1)))
        distinct_tasks = max(len(task_ids), int(previous.get("distinct_tasks", 1)))
        return {
            "occurrences": occurrences,
            "distinct_tasks": distinct_tasks,
            "policy_candidate": distinct_tasks >= 3,
        }

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(str(value) for value in values if str(value)))
