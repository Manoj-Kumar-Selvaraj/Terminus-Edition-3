"""Measured learning loop for Terminus human-writing calibration."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


class LearningLoopError(ValueError):
    """Raised when an outcome record violates the learning schema."""


class HumanWritingLearningStore:
    """Record task outcomes without storing prior instruction wording."""

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
            / "human-writing-outcomes.jsonl"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        registry_path = self.root / ".terminus" / "human_writing" / "dataset_registry.json"
        adapter_path = self.root / ".terminus" / "human_writing" / "adapter_policy.json"
        self.registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.adapter_policy = json.loads(adapter_path.read_text(encoding="utf-8"))

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        """Append one outcome after stripping any prohibited text surface."""
        forbidden = {
            "instruction",
            "instruction_text",
            "draft_text",
            "accepted_text",
            "source_text",
            "verifier_body",
            "oracle_diff",
        }
        leaked = sorted(forbidden & set(record))
        if leaked:
            raise LearningLoopError(f"outcome record contains prohibited text fields: {leaked}")
        required = {
            "task_id",
            "task_commit",
            "calibration_pair_id",
            "writer_calibration_id",
            "reviewer_calibration_id",
            "draft_sha256",
            "accepted_sha256",
            "requirement_count",
            "revision_count",
            "dataset_usage",
            "reviewer_results",
        }
        missing = sorted(required - set(record))
        if missing:
            raise LearningLoopError(f"missing outcome fields: {missing}")
        if not isinstance(record["dataset_usage"], dict):
            raise LearningLoopError("dataset_usage must be an object")
        if not isinstance(record["reviewer_results"], dict):
            raise LearningLoopError("reviewer_results must be an object")
        if int(record["requirement_count"]) < 1:
            raise LearningLoopError("requirement_count must be positive")
        if int(record["revision_count"]) < 0:
            raise LearningLoopError("revision_count cannot be negative")

        payload = {"schema_version": self.schema_version, **record}
        payload["record_id"] = "hwout-" + _stable_hash(payload)[:20]
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return payload

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        values = []
        for line_no, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LearningLoopError(
                    f"invalid learning JSONL line {line_no}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise LearningLoopError(f"learning JSONL line {line_no} is not an object")
            values.append(value)
        return values

    def metrics(self) -> dict[str, Any]:
        records = self.records()
        task_count = len({record["task_id"] for record in records})
        revisions = [int(record.get("revision_count", 0)) for record in records]
        initial_passes = 0
        final_passes = 0
        llmaj_writing_findings = 0
        disagreement_classes: dict[str, int] = defaultdict(int)
        dataset_quality: dict[str, list[float]] = defaultdict(list)
        ab_decided = 0
        ab_calibrated_wins = 0

        for record in records:
            reviewers = record.get("reviewer_results", {})
            instruction = reviewers.get("instruction_reviewer")
            human = reviewers.get("human_quality_reviewer")
            if instruction == "PASS":
                initial_passes += 1
            if record.get("final_instruction_status") == "PASS":
                final_passes += 1
            if record.get("llmaj_writing_finding") is True:
                llmaj_writing_findings += 1
            if instruction and human and instruction != human:
                key = f"instruction_reviewer={instruction}|human_quality={human}"
                disagreement_classes[key] += 1

            quality = _quality_score(record)
            for dataset_id, usage in record.get("dataset_usage", {}).items():
                if _usage_count(usage) > 0:
                    dataset_quality[dataset_id].append(quality)

            ab_result = record.get("ab_result")
            if isinstance(ab_result, dict):
                preferred = ab_result.get("preferred_origin")
                if preferred in {"baseline", "calibrated"}:
                    ab_decided += 1
                    if preferred == "calibrated":
                        ab_calibrated_wins += 1

        disagreement_count = sum(disagreement_classes.values())
        return {
            "schema_version": self.schema_version,
            "record_count": len(records),
            "task_count": task_count,
            "average_revision_count": sum(revisions) / len(revisions) if revisions else None,
            "initial_instruction_pass_rate": initial_passes / len(records) if records else None,
            "final_instruction_pass_rate": final_passes / len(records) if records else None,
            "llmaj_writing_finding_rate": llmaj_writing_findings / len(records) if records else None,
            "reviewer_disagreement_count": disagreement_count,
            "reviewer_disagreement_rate": disagreement_count / len(records) if records else None,
            "reviewer_disagreement_classes": dict(sorted(disagreement_classes.items())),
            "ab_decided": ab_decided,
            "ab_calibrated_win_rate": ab_calibrated_wins / ab_decided if ab_decided else None,
            "dataset_quality": {
                dataset_id: {
                    "task_count": len(scores),
                    "mean_quality": sum(scores) / len(scores),
                }
                for dataset_id, scores in sorted(dataset_quality.items())
            },
        }

    def recommend_weights(self, role: str) -> dict[str, Any]:
        """Recommend bounded evidence-based changes; never mutate the registry."""
        if role not in {"writer", "reviewer"}:
            raise LearningLoopError("role must be writer or reviewer")
        records = self.records()
        policy = self.registry["empirical_adjustment"]
        min_tasks = int(policy["minimum_tasks_before_recommendation"])
        distinct_tasks = len({record["task_id"] for record in records})
        if distinct_tasks < min_tasks:
            return {
                "status": "INSUFFICIENT_DATA",
                "role": role,
                "task_count": distinct_tasks,
                "required_task_count": min_tasks,
                "recommendation": {},
            }

        datasets = [
            dataset
            for dataset in self.registry["datasets"]
            if dataset.get("enabled") is True and dataset.get(f"{role}_weight", 0) > 0
        ]
        quality_by_dataset: dict[str, list[float]] = defaultdict(list)
        for record in records:
            score = _quality_score(record)
            for dataset_id, usage in record.get("dataset_usage", {}).items():
                if _usage_count(usage) > 0:
                    quality_by_dataset[dataset_id].append(score)
        means = {
            dataset["id"]: (
                sum(quality_by_dataset[dataset["id"]]) / len(quality_by_dataset[dataset["id"]])
                if quality_by_dataset[dataset["id"]]
                else 0.0
            )
            for dataset in datasets
        }
        overall = sum(means.values()) / len(means) if means else 0.0
        cap = float(policy["maximum_absolute_weight_change_per_release"])
        raw: dict[str, float] = {}
        for dataset in datasets:
            current = float(dataset[f"{role}_weight"])
            direction = means[dataset["id"]] - overall
            delta = max(-cap, min(cap, direction * 0.05))
            raw[dataset["id"]] = max(0.0, current + delta)
        total = sum(raw.values())
        normalized = {
            dataset_id: round(weight / total, 6) if total else 0.0
            for dataset_id, weight in raw.items()
        }
        return {
            "status": "RECOMMENDATION_READY",
            "role": role,
            "task_count": distinct_tasks,
            "current_weights": {
                dataset["id"]: dataset[f"{role}_weight"] for dataset in datasets
            },
            "recommended_weights": normalized,
            "automatic_registry_mutation": False,
            "approval_required": True,
            "basis": "quality scores from tasks where each dataset contributed calibration",
        }

    def adapter_readiness(self) -> dict[str, Any]:
        """Gate future adapter training on accumulated evidence and holdouts."""
        records = self.records()
        policy = self.adapter_policy
        task_count = len({record["task_id"] for record in records})
        preference_pairs = sum(
            record.get("accepted_sha256") != record.get("draft_sha256") for record in records
        )
        metrics = self.metrics()
        holdout = sum(record.get("holdout_eligible") is True for record in records)
        win_rate = metrics["ab_calibrated_win_rate"]
        checks = {
            "minimum_distinct_tasks": task_count >= policy["minimum_distinct_tasks"],
            "minimum_preference_pairs": preference_pairs >= policy["minimum_preference_pairs"],
            "minimum_holdout_cases": holdout >= policy["minimum_holdout_cases"],
            "minimum_blind_ab_win_rate": win_rate is not None
            and win_rate >= policy["minimum_blind_ab_calibrated_win_rate"],
            "no_requirement_regression": all(
                record.get("requirement_regression") is not True for record in records
            ),
        }
        return {
            "status": "READY_FOR_HUMAN_APPROVAL" if all(checks.values()) else "NOT_READY",
            "enabled": policy["enabled"],
            "checks": checks,
            "task_count": task_count,
            "preference_pairs": preference_pairs,
            "holdout_cases": holdout,
            "blind_ab_calibrated_win_rate": win_rate,
            "approval_required": True,
            "separate_writer_reviewer_adapters": True,
        }


def _usage_count(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        return int(value.get("sample_count", 0))
    return 0


def _quality_score(record: dict[str, Any]) -> float:
    completeness = 1.0 if record.get("requirement_completeness") == "SUFFICIENT" else 0.0
    human_signal = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.0}.get(
        record.get("human_signal"), 0.5
    )
    final_pass = 1.0 if record.get("final_instruction_status") == "PASS" else 0.0
    llmaj = 0.0 if record.get("llmaj_writing_finding") is True else 1.0
    return 0.45 * completeness + 0.20 * human_signal + 0.25 * final_pass + 0.10 * llmaj


def _stable_hash(value: Any) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
