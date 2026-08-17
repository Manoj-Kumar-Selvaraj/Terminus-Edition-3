"""No-text Terminus-native preference references for future training/evaluation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class PreferenceStoreError(ValueError):
    """Raised when a preference reference is malformed."""


class TerminusPreferenceStore:
    """Persist chosen/rejected references without exposing prior wording at task time."""

    schema_version = "1.0"

    def __init__(self, root: Path, path: Path | None = None):
        self.root = root.resolve()
        self.path = (
            path
            if path is not None
            else self.root
            / ".terminus"
            / "learning"
            / "state"
            / "human-writing-preferences.jsonl"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        *,
        task_id: str,
        task_commit: str,
        rejected_text: str,
        chosen_text: str,
        label_source: str,
        reason_codes: list[str],
        calibration_pair_id: str,
        holdout_eligible: bool,
    ) -> dict[str, Any]:
        if not rejected_text.strip() or not chosen_text.strip():
            raise PreferenceStoreError("chosen/rejected texts must be non-empty")
        if rejected_text == chosen_text:
            raise PreferenceStoreError("chosen and rejected texts must differ")
        record = {
            "schema_version": self.schema_version,
            "task_id": task_id,
            "task_commit": task_commit,
            "rejected_sha256": _sha(rejected_text),
            "chosen_sha256": _sha(chosen_text),
            "label_source": label_source,
            "reason_codes": sorted(set(reason_codes)),
            "calibration_pair_id": calibration_pair_id,
            "holdout_eligible": bool(holdout_eligible),
            "content_resolution": (
                "Resolve exact historical task/commit artifacts only in an offline "
                "training/evaluation job. Never project historical wording into a "
                "new task-time writer pack."
            ),
        }
        record["preference_id"] = "hwpref-" + _hash(record)[:20]
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def summary(self) -> dict[str, Any]:
        records = self.records()
        return {
            "schema_version": self.schema_version,
            "preference_count": len(records),
            "distinct_tasks": len({record["task_id"] for record in records}),
            "holdout_count": sum(record.get("holdout_eligible") is True for record in records),
            "label_sources": sorted({record["label_source"] for record in records}),
        }


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
