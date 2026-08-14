"""Ingest human, reviewer, CI, LLMaJ, trial and difficulty signals uniformly."""

from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .model import FeedbackSource, Severity, content_hash, feedback_identity
from .registry import LearningStore
from .schema_validation import LearningSchemaValidator


class FeedbackIngestor:
    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)

    def capture(
        self,
        *,
        source_type: FeedbackSource | str,
        producer: str,
        task_id: str,
        task_commit: str,
        severity: Severity | str,
        message: str,
        category: str | None = None,
        stage_hint: str | None = None,
        role_hint: str | None = None,
        run_id: str | int | None = None,
        external_ref: str | None = None,
        evidence: list[dict[str, Any]] | None = None,
        test_id: str | None = None,
        metric: str | None = None,
        value: Any = None,
        expected: Any = None,
        captured_at: str | None = None,
    ) -> dict[str, Any]:
        if not producer.strip() or not task_id.strip() or not message.strip():
            raise ValueError("producer, task_id and message are required")
        self._require_commit(task_commit)
        source = {"type": FeedbackSource(source_type).value, "producer": producer.strip()}
        if run_id is not None:
            source["run_id"] = run_id
        if external_ref:
            source["external_ref"] = external_ref
        observation: dict[str, Any] = {
            "severity": Severity(severity).value,
            "message": message.strip(),
        }
        for key, item in {
            "category": category,
            "stage_hint": stage_hint,
            "role_hint": role_hint,
            "test_id": test_id,
            "metric": metric,
        }.items():
            if item:
                observation[key] = item
        if value is not None:
            observation["value"] = value
        if expected is not None:
            observation["expected"] = expected
        if evidence:
            observation["evidence"] = evidence
        event: dict[str, Any] = {
            "schema_version": "1.0",
            "source": source,
            "task": {"task_id": task_id, "task_commit": task_commit},
            "observation": observation,
            "provenance": {
                "captured_at": captured_at
                or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                "content_hash": "",
            },
        }
        event["provenance"]["content_hash"] = content_hash(
            {key: value for key, value in event.items() if key != "provenance"}
        )
        event["feedback_id"] = feedback_identity(event)
        self.schemas.validate("feedback", event)
        self.store.feedback.append(event)
        return event

    def _require_commit(self, commit: str) -> None:
        result = subprocess.run(
            ["git", "-C", str(self.root), "cat-file", "-e", f"{commit}^{{commit}}"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ValueError(f"task_commit is not available in repository history: {commit}")
