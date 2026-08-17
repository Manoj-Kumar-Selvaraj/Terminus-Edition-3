"""Measured, provenance-bound learning loop for Terminus human-writing calibration."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from calibration import HumanWritingCalibrationPlanner
from preference_store import TerminusPreferenceStore

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_TEXT_KEYS = {
    "instruction",
    "instruction_text",
    "draft_text",
    "accepted_text",
    "source_text",
    "verifier_body",
    "oracle_diff",
    "prompt_text",
}
_REVIEW_VALUES = {"PASS", "REVISE", "BLOCKED", "NOT_RUN", "INSUFFICIENT_EVIDENCE"}


class LearningLoopError(ValueError):
    """Raised when an outcome record violates the learning schema or provenance."""


class HumanWritingLearningStore:
    """Record task outcomes without storing prior instruction wording."""

    schema_version = "1.1"

    def __init__(self, root: Path, path: Path | None = None):
        self.root = root.resolve()
        self.path = path if path is not None else (
            self.root
            / ".terminus"
            / "learning"
            / "knowledge"
            / "human-writing-outcomes.jsonl"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        registry_path = self.root / ".terminus" / "human_writing" / "dataset_registry.json"
        adapter_path = self.root / ".terminus" / "human_writing" / "adapter_policy.json"
        self.registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.adapter_policy = json.loads(adapter_path.read_text(encoding="utf-8"))
        self.datasets = {dataset["id"]: dataset for dataset in self.registry["datasets"]}

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        """Append one no-text outcome after exact task/calibration validation."""
        leaked = _find_forbidden_keys(record)
        if leaked:
            raise LearningLoopError(
                f"outcome record contains prohibited text fields: {sorted(leaked)}"
            )
        required = {
            "task_id",
            "task_commit",
            "domain",
            "calibration_pair_id",
            "writer_calibration_id",
            "reviewer_calibration_id",
            "draft_sha256",
            "accepted_sha256",
            "requirement_count",
            "requirement_completeness",
            "requirement_regression",
            "revision_count",
            "dataset_usage",
            "reviewer_results",
            "final_instruction_status",
            "human_signal",
            "llmaj_writing_finding",
            "contamination_status",
            "evidence_refs",
        }
        missing = sorted(required - set(record))
        if missing:
            raise LearningLoopError(f"missing outcome fields: {missing}")
        self._validate_binding(record)

        payload = {"schema_version": self.schema_version, **record}
        payload["record_id"] = "hwout-" + _stable_hash(payload)[:20]
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return payload

    def _validate_binding(self, record: dict[str, Any]) -> None:
        task_commit = str(record["task_commit"])
        if not _SHA40.fullmatch(task_commit):
            raise LearningLoopError("task_commit must be a full 40-character SHA")
        for field in ("draft_sha256", "accepted_sha256"):
            if not _SHA256.fullmatch(str(record[field])):
                raise LearningLoopError(f"{field} must be SHA-256")
        committed_instruction = self._git_file(
            task_commit, f"{record['task_id']}/instruction.md"
        )
        if committed_instruction is None:
            raise LearningLoopError("task_commit does not contain task instruction.md")
        accepted_sha = hashlib.sha256(committed_instruction.encode()).hexdigest()
        if accepted_sha != record["accepted_sha256"]:
            raise LearningLoopError(
                "accepted_sha256 does not match instruction.md at task_commit"
            )

        planner = HumanWritingCalibrationPlanner(self.root)
        pair = planner.build_pair(task_id=str(record["task_id"]), domain=str(record["domain"]))
        expected = {
            "calibration_pair_id": pair["pair_id"],
            "writer_calibration_id": pair["writer"]["calibration_id"],
            "reviewer_calibration_id": pair["reviewer"]["calibration_id"],
        }
        for field, value in expected.items():
            if record[field] != value:
                raise LearningLoopError(f"stale or forged calibration binding: {field}")

        if int(record["requirement_count"]) < 1:
            raise LearningLoopError("requirement_count must be positive")
        if int(record["revision_count"]) < 0:
            raise LearningLoopError("revision_count cannot be negative")
        if record["requirement_completeness"] not in {"SUFFICIENT", "INSUFFICIENT"}:
            raise LearningLoopError("invalid requirement_completeness")
        if not isinstance(record["requirement_regression"], bool):
            raise LearningLoopError("requirement_regression must be explicit boolean")
        if record["final_instruction_status"] not in {"PASS", "REVISE", "BLOCKED"}:
            raise LearningLoopError("invalid final_instruction_status")
        if record["human_signal"] not in {"HIGH", "MEDIUM", "LOW"}:
            raise LearningLoopError("invalid human_signal")
        if not isinstance(record["llmaj_writing_finding"], bool):
            raise LearningLoopError("llmaj_writing_finding must be boolean")
        if record["contamination_status"] not in {
            "PASS",
            "REWRITE_REQUIRED",
            "SKIPPED_NO_RAW_TEXT",
        }:
            raise LearningLoopError("invalid contamination_status")

        usage = record["dataset_usage"]
        if not isinstance(usage, dict):
            raise LearningLoopError("dataset_usage must be an object")
        unknown = set(usage) - set(self.datasets)
        if unknown:
            raise LearningLoopError(f"unknown dataset ids in usage: {sorted(unknown)}")
        for dataset_id, value in usage.items():
            if self.datasets[dataset_id].get("enabled") is not True and _usage_count(value) > 0:
                raise LearningLoopError(f"disabled dataset used in outcome: {dataset_id}")

        reviewers = record["reviewer_results"]
        if not isinstance(reviewers, dict):
            raise LearningLoopError("reviewer_results must be an object")
        for reviewer, value in reviewers.items():
            if value not in _REVIEW_VALUES:
                raise LearningLoopError(f"invalid reviewer result {reviewer}={value}")
        evidence_refs = record["evidence_refs"]
        if not isinstance(evidence_refs, dict) or not evidence_refs.get(
            "instruction_reviewer_result_id"
        ):
            raise LearningLoopError(
                "evidence_refs requires instruction_reviewer_result_id"
            )

        ab_result = record.get("ab_result")
        if isinstance(ab_result, dict) and (
            ab_result.get("evaluator_binding", {}).get("independent_from_writer") is not True
        ):
            raise LearningLoopError("A/B result is not independently evaluator-bound")
        self._validate_ablation(record.get("dataset_ablation", {}))

    def _validate_ablation(self, value: Any) -> None:
        if value in ({}, None):
            return
        if not isinstance(value, dict):
            raise LearningLoopError("dataset_ablation must be an object")
        for dataset_id, observation in value.items():
            if dataset_id not in self.datasets:
                raise LearningLoopError(f"unknown ablation dataset: {dataset_id}")
            if not isinstance(observation, dict):
                raise LearningLoopError("ablation observation must be an object")
            if observation.get("controlled") is not True:
                raise LearningLoopError("ablation evidence must be controlled")
            if observation.get("role") not in {"writer", "reviewer"}:
                raise LearningLoopError("ablation role must be writer or reviewer")
            delta = observation.get("quality_delta")
            if not isinstance(delta, (int, float)) or not -1.0 <= float(delta) <= 1.0:
                raise LearningLoopError("ablation quality_delta must be between -1 and 1")

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        values: list[dict[str, Any]] = []
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
        revisions = [int(record.get("revision_count", 0)) for record in records]
        disagreement_classes: dict[str, int] = defaultdict(int)
        dataset_exposure_quality: dict[str, list[float]] = defaultdict(list)
        ab_decided = 0
        ab_calibrated_wins = 0
        initial_passes = 0
        final_passes = 0
        llmaj_findings = 0
        for record in records:
            reviewers = record.get("reviewer_results", {})
            instruction = reviewers.get("instruction_reviewer")
            human = reviewers.get("human_quality_reviewer")
            if instruction == "PASS":
                initial_passes += 1
            if record.get("final_instruction_status") == "PASS":
                final_passes += 1
            if record.get("llmaj_writing_finding") is True:
                llmaj_findings += 1
            if instruction and human and instruction != human:
                disagreement_classes[
                    f"instruction_reviewer={instruction}|human_quality={human}"
                ] += 1
            quality = _quality_score(record)
            for dataset_id, usage in record.get("dataset_usage", {}).items():
                if _usage_count(usage) > 0:
                    dataset_exposure_quality[dataset_id].append(quality)
            ab_result = record.get("ab_result")
            if isinstance(ab_result, dict):
                preferred = ab_result.get("preferred_origin")
                if preferred in {"baseline", "calibrated"}:
                    ab_decided += 1
                    ab_calibrated_wins += preferred == "calibrated"

        disagreement_count = sum(disagreement_classes.values())
        return {
            "schema_version": self.schema_version,
            "record_count": len(records),
            "task_count": len({record["task_id"] for record in records}),
            "average_revision_count": sum(revisions) / len(revisions) if revisions else None,
            "initial_instruction_pass_rate": initial_passes / len(records) if records else None,
            "final_instruction_pass_rate": final_passes / len(records) if records else None,
            "llmaj_writing_finding_rate": llmaj_findings / len(records) if records else None,
            "reviewer_disagreement_count": disagreement_count,
            "reviewer_disagreement_rate": disagreement_count / len(records) if records else None,
            "reviewer_disagreement_classes": dict(sorted(disagreement_classes.items())),
            "ab_decided": ab_decided,
            "ab_calibrated_win_rate": ab_calibrated_wins / ab_decided if ab_decided else None,
            "dataset_exposure_quality": {
                dataset_id: {
                    "task_count": len(scores),
                    "mean_quality": sum(scores) / len(scores),
                    "causal_for_weighting": False,
                }
                for dataset_id, scores in sorted(dataset_exposure_quality.items())
            },
        }

    def recommend_weights(self, role: str) -> dict[str, Any]:
        """Recommend bounded changes only from controlled dataset ablations."""
        if role not in {"writer", "reviewer"}:
            raise LearningLoopError("role must be writer or reviewer")
        records = self.records()
        policy = self.registry["empirical_adjustment"]
        min_tasks = int(policy["minimum_tasks_before_recommendation"])
        min_ablation = int(policy["minimum_ablation_observations_per_dataset"])
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
            if dataset.get("enabled") is True
            and role in dataset.get("allowed_roles", [])
            and dataset.get(f"{role}_weight", 0) > 0
        ]
        deltas: dict[str, list[float]] = defaultdict(list)
        for record in records:
            for dataset_id, observation in record.get("dataset_ablation", {}).items():
                if observation.get("role") == role and observation.get("controlled") is True:
                    deltas[dataset_id].append(float(observation["quality_delta"]))
        counts = {dataset["id"]: len(deltas[dataset["id"]]) for dataset in datasets}
        insufficient = {
            dataset_id: count
            for dataset_id, count in counts.items()
            if count < min_ablation
        }
        if insufficient:
            return {
                "status": "INSUFFICIENT_ATTRIBUTION",
                "role": role,
                "task_count": distinct_tasks,
                "minimum_ablation_observations_per_dataset": min_ablation,
                "ablation_counts": counts,
                "insufficient": insufficient,
                "recommendation": {},
            }

        means = {
            dataset["id"]: sum(deltas[dataset["id"]]) / len(deltas[dataset["id"]])
            for dataset in datasets
        }
        cap = float(policy["maximum_absolute_weight_change_per_release"])
        raw: dict[str, float] = {}
        for dataset in datasets:
            current = float(dataset[f"{role}_weight"])
            delta = max(-cap, min(cap, means[dataset["id"]] * 0.10))
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
            "ablation_counts": counts,
            "mean_controlled_quality_delta": means,
            "current_weights": {
                dataset["id"]: dataset[f"{role}_weight"] for dataset in datasets
            },
            "recommended_weights": normalized,
            "automatic_registry_mutation": False,
            "approval_required": True,
            "basis": "controlled per-dataset ablation quality deltas",
        }

    def adapter_readiness(self) -> dict[str, Any]:
        """Gate future adapter training on real preferences, holdouts and regressions."""
        records = self.records()
        policy = self.adapter_policy
        preferences = TerminusPreferenceStore(self.root).records()
        task_count = len({record["task_id"] for record in records})
        preference_pairs = len(preferences)
        holdout = sum(
            preference.get("holdout_eligible") is True
            and preference.get("chosen_task_artifact_bound") is True
            for preference in preferences
        )
        metrics = self.metrics()
        win_rate = metrics["ab_calibrated_win_rate"]
        checks = {
            "minimum_distinct_tasks": task_count >= policy["minimum_distinct_tasks"],
            "minimum_preference_pairs": preference_pairs >= policy["minimum_preference_pairs"],
            "minimum_holdout_cases": holdout >= policy["minimum_holdout_cases"],
            "minimum_blind_ab_win_rate": win_rate is not None
            and win_rate >= policy["minimum_blind_ab_calibrated_win_rate"],
            "no_requirement_regression": bool(records)
            and all(record.get("requirement_regression") is False for record in records),
        }
        if policy.get("enabled") is not True:
            status = "DISABLED"
        else:
            status = "READY_FOR_HUMAN_APPROVAL" if all(checks.values()) else "NOT_READY"
        return {
            "status": status,
            "enabled": policy.get("enabled") is True,
            "checks": checks,
            "task_count": task_count,
            "preference_pairs": preference_pairs,
            "holdout_cases": holdout,
            "blind_ab_calibrated_win_rate": win_rate,
            "approval_required": True,
            "separate_writer_reviewer_adapters": True,
        }

    def _git_file(self, commit: str, path: str) -> str | None:
        result = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{commit}:{path}"],
            capture_output=True,
            text=True,
        )
        return result.stdout if result.returncode == 0 else None


def _find_forbidden_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in _FORBIDDEN_TEXT_KEYS:
                found.add(key)
            found.update(_find_forbidden_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            found.update(_find_forbidden_keys(nested))
    return found


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
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
