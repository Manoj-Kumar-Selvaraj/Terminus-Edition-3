"""No-text Terminus-native preference references for future training/evaluation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_INDEPENDENT_LABEL_SOURCES = {
    "instruction_reviewer",
    "human_quality_reviewer",
    "blind_ab_evaluator",
    "human_review",
}


class PreferenceStoreError(ValueError):
    """Raised when a preference reference is malformed or unbound."""


class TerminusPreferenceStore:
    """Persist chosen/rejected references without exposing prior wording at task time."""

    schema_version = "1.1"

    def __init__(self, root: Path, path: Path | None = None):
        self.root = root.resolve()
        self.path = path if path is not None else (
            self.root
            / ".terminus"
            / "learning"
            / "knowledge"
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
        if not _SHA40.fullmatch(task_commit):
            raise PreferenceStoreError("task_commit must be a full 40-character SHA")
        if not calibration_pair_id.startswith("hwpair-"):
            raise PreferenceStoreError("invalid calibration_pair_id")
        if label_source not in _INDEPENDENT_LABEL_SOURCES:
            raise PreferenceStoreError(f"unsupported independent label_source: {label_source}")
        clean_reasons = sorted({reason for reason in reason_codes if reason.strip()})
        if not clean_reasons:
            raise PreferenceStoreError("at least one reason code is required")

        chosen_sha = _sha(chosen_text)
        committed = self._git_file(task_commit, f"{task_id}/instruction.md")
        if committed is None:
            raise PreferenceStoreError(
                "chosen preference cannot be bound to task_commit instruction.md"
            )
        if _sha(committed) != chosen_sha:
            raise PreferenceStoreError(
                "chosen text hash does not match instruction.md at task_commit"
            )
        if holdout_eligible and "requirements_preserved" not in clean_reasons:
            raise PreferenceStoreError(
                "holdout preference requires requirements_preserved reason code"
            )

        record = {
            "schema_version": self.schema_version,
            "task_id": task_id,
            "task_commit": task_commit,
            "rejected_sha256": _sha(rejected_text),
            "chosen_sha256": chosen_sha,
            "label_source": label_source,
            "reason_codes": clean_reasons,
            "calibration_pair_id": calibration_pair_id,
            "holdout_eligible": bool(holdout_eligible),
            "chosen_task_artifact_bound": True,
            "content_resolution": (
                "Resolve exact historical content only in an authorized offline "
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
        records: list[dict[str, Any]] = []
        for line_no, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise PreferenceStoreError(f"preference line {line_no} is not an object")
            records.append(value)
        return records

    def summary(self) -> dict[str, Any]:
        records = self.records()
        return {
            "schema_version": self.schema_version,
            "preference_count": len(records),
            "distinct_tasks": len({record["task_id"] for record in records}),
            "holdout_count": sum(record.get("holdout_eligible") is True for record in records),
            "bound_count": sum(
                record.get("chosen_task_artifact_bound") is True for record in records
            ),
            "label_sources": sorted({record["label_source"] for record in records}),
        }

    def _git_file(self, commit: str, path: str) -> str | None:
        result = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{commit}:{path}"],
            capture_output=True,
            text=True,
        )
        return result.stdout if result.returncode == 0 else None


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
