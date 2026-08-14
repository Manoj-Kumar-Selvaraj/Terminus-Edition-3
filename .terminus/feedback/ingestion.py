"""Ingest human, reviewer, CI, LLMaJ, trial and difficulty signals uniformly."""

from __future__ import annotations

import copy
import datetime as dt
import subprocess
from pathlib import Path
from typing import Any, Mapping

from execution.evidence_refs import EvidenceReferenceVerifier

from .model import FeedbackSource, Severity, content_hash, feedback_identity
from .provenance import ProvenanceValidator
from .registry import LearningStore
from .schema_validation import LearningSchemaValidator


class FeedbackIngestor:
    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)
        self.evidence = EvidenceReferenceVerifier(self.root)
        self.provenance = ProvenanceValidator(self.root)

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
        source_binding: Mapping[str, Any] | None = None,
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
        source_kind = FeedbackSource(source_type)
        source = {"type": source_kind.value, "producer": producer.strip()}
        if run_id is not None:
            source["run_id"] = run_id
        if external_ref:
            source["external_ref"] = external_ref

        validated_binding = self._source_binding(
            source_kind=source_kind,
            producer=producer.strip(),
            task_id=task_id,
            task_commit=task_commit,
            run_id=run_id,
            source_binding=source_binding,
        )
        if source_kind is FeedbackSource.HUMAN_REVIEW:
            trust_status = "HUMAN_ASSERTED"
        elif self.evidence.is_resolved(validated_binding):
            trust_status = "REPOSITORY_RESOLVED"
        else:
            trust_status = "EXTERNAL_POINTER_ONLY"

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
            observation["evidence"] = [
                self.evidence.validate(item, index)
                for index, item in enumerate(evidence)
            ]

        captured = captured_at or dt.datetime.now(dt.timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
        event: dict[str, Any] = {
            "schema_version": "1.0",
            "source": source,
            "task": {"task_id": task_id, "task_commit": task_commit},
            "observation": observation,
            "provenance": {
                "captured_at": captured,
                "content_hash": "",
                "trust_status": trust_status,
                "source_binding": validated_binding,
            },
        }
        hash_payload = copy.deepcopy(event)
        hash_payload["provenance"].pop("content_hash", None)
        event["provenance"]["content_hash"] = content_hash(hash_payload)
        event["feedback_id"] = feedback_identity(event)
        self.schemas.validate("feedback", event)
        self.store.feedback.append(event)
        return event

    def _source_binding(
        self,
        *,
        source_kind: FeedbackSource,
        producer: str,
        task_id: str,
        task_commit: str,
        run_id: str | int | None,
        source_binding: Mapping[str, Any] | None,
    ) -> dict[str, Any] | None:
        if source_kind is FeedbackSource.HUMAN_REVIEW:
            if source_binding is None:
                return None
            return self.evidence.validate(source_binding, 0)
        if source_binding is None:
            raise ValueError(
                f"{source_kind.value} feedback requires immutable source_binding evidence"
            )
        return self.provenance.validate_source_binding(
            source_type=source_kind.value,
            producer=producer,
            task_id=task_id,
            task_commit=task_commit,
            run_id=run_id,
            binding=source_binding,
        )

    def _require_commit(self, commit: str) -> None:
        result = subprocess.run(
            ["git", "-C", str(self.root), "cat-file", "-e", f"{commit}^{{commit}}"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ValueError(f"task_commit is not available in repository history: {commit}")
