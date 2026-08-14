"""Project generalized lessons to agents without exposing raw historical findings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from feedback.registry import LearningStore
from feedback.schema_validation import LearningSchemaValidator


class LearningProjector:
    """Return only generalized lesson content relevant to a stage/role.

    Raw feedback, task-specific text, source finding IDs, task IDs and prior
    reviewer conclusions are intentionally omitted from executor-facing output.
    """

    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)

    def project(
        self,
        *,
        stage_id: str,
        role_id: str,
        domain: str | None = None,
        limit: int = 12,
    ) -> dict[str, Any]:
        if limit < 0:
            raise ValueError("learning projection limit cannot be negative")
        projected: list[dict[str, Any]] = []
        for lesson in self.store.lessons.read():
            self.schemas.validate("lesson", lesson)
            if lesson.get("state") != "ACTIVE":
                continue
            targets = lesson["targets"]
            stage_match = not targets["stages"] or stage_id in targets["stages"]
            role_match = not targets["roles"] or role_id in targets["roles"]
            domain_match = (
                not targets.get("domains")
                or domain is None
                or domain in targets.get("domains", [])
            )
            if not (stage_match and role_match and domain_match):
                continue
            projected.append(
                {
                    "lesson_id": lesson["lesson_id"],
                    "category": lesson["category"],
                    "failure_pattern": lesson["failure_pattern"],
                    "future_rule": lesson["future_rule"],
                }
            )
        projected.sort(key=lambda item: (item["category"], item["lesson_id"]))
        selected = projected[:limit]
        return {
            "mode": "GENERALIZED_LESSONS_ONLY",
            "stage_id": stage_id,
            "role_id": role_id,
            "lessons": selected,
            "lesson_count": len(selected),
            "raw_feedback_exposed": False,
            "raw_findings_exposed": False,
        }
