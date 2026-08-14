"""Project generalized lessons to agents without exposing raw historical findings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from feedback.registry import LearningStore
from feedback.schema_validation import LearningSchemaValidator

from .integrity import LearningIntegrityValidator


class LearningProjector:
    """Return only independently derived generalized lesson content.

    Raw feedback, task-specific text, source finding IDs, task IDs and prior
    reviewer conclusions are intentionally omitted from executor-facing output.
    An ACTIVE registry row is persistence, not authority: every projected lesson
    replays its source finding closure and promotion proof first.
    """

    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)
        self.integrity = LearningIntegrityValidator(self.root, store=self.store)

    def project(
        self,
        *,
        stage_id: str,
        role_id: str,
        domain: str | None = None,
        limit: int = 12,
        chain_head: str | None = None,
    ) -> dict[str, Any]:
        if limit < 0:
            raise ValueError("learning projection limit cannot be negative")
        projected: list[dict[str, Any]] = []
        lessons = self.store.lessons.latest_by("lesson_id", chain_head=chain_head)
        for lesson in lessons:
            self.schemas.validate("lesson", lesson)
            if lesson.get("state") != "ACTIVE":
                continue
            self.integrity.validate_lesson(lesson)
            targets = lesson["targets"]
            stage_match = stage_id in targets["stages"]
            role_match = role_id in targets["roles"]
            target_domains = targets.get("domains", [])
            domain_match = not target_domains or (
                domain is not None and domain in target_domains
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
