"""Deterministic dataset-backed calibration planning for instruction writing.

The planner never vendors or downloads external dataset bodies. It validates the
curated dataset registry, creates disjoint writer/reviewer local study sets, and
emits external sampling requirements for the Human Writing Research stage.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


class CalibrationError(ValueError):
    """Raised when the calibration registry or seed catalog is invalid."""


class HumanWritingCalibrationPlanner:
    """Build deterministic, independent writer and reviewer calibration packs."""

    schema_version = "1.0"
    _ROLE_KINDS = {
        "writer": {"human_issue": 6, "constraint_pair": 2, "anti_template": 1},
        "reviewer": {"human_issue": 6, "constraint_pair": 3, "anti_template": 2},
    }

    def __init__(self, root: Path):
        self.root = root.resolve()
        base = self.root / ".terminus" / "human_writing"
        self.registry = self._load_json(base / "dataset_registry.json")
        self.catalog = self._load_json(base / "seed_catalog.json")
        self.validate()

    def validate(self) -> dict[str, Any]:
        """Validate registry weights, dataset state, and seed provenance."""
        datasets = self.registry.get("datasets")
        if not isinstance(datasets, list) or not datasets:
            raise CalibrationError("dataset registry must contain datasets")
        ids: set[str] = set()
        enabled_ids: set[str] = set()
        for dataset in datasets:
            if not isinstance(dataset, dict):
                raise CalibrationError("dataset registry entries must be objects")
            dataset_id = dataset.get("id")
            if not isinstance(dataset_id, str) or not dataset_id:
                raise CalibrationError("every dataset requires a non-empty id")
            if dataset_id in ids:
                raise CalibrationError(f"duplicate dataset id: {dataset_id}")
            ids.add(dataset_id)
            enabled = dataset.get("enabled") is True
            if enabled:
                enabled_ids.add(dataset_id)
            for role in ("writer", "reviewer"):
                weight = dataset.get(f"{role}_weight")
                if not isinstance(weight, (int, float)) or weight < 0:
                    raise CalibrationError(f"invalid {role} weight for {dataset_id}")
                if not enabled and weight != 0:
                    raise CalibrationError(
                        f"disabled dataset {dataset_id} must have zero {role} weight"
                    )

        for role in ("writer", "reviewer"):
            total = sum(
                float(dataset[f"{role}_weight"])
                for dataset in datasets
                if dataset.get("enabled") is True
            )
            if abs(total - 1.0) > 1e-9:
                raise CalibrationError(f"enabled {role} weights must sum to 1.0, got {total}")

        samples = self.catalog.get("samples")
        if not isinstance(samples, list) or not samples:
            raise CalibrationError("seed catalog must contain samples")
        sample_ids: set[str] = set()
        counts: dict[str, int] = {}
        for sample in samples:
            if not isinstance(sample, dict):
                raise CalibrationError("seed samples must be objects")
            sample_id = sample.get("id")
            if not isinstance(sample_id, str) or not sample_id:
                raise CalibrationError("every seed sample requires a non-empty id")
            if sample_id in sample_ids:
                raise CalibrationError(f"duplicate seed sample id: {sample_id}")
            sample_ids.add(sample_id)
            source_dataset = sample.get("source_dataset")
            if source_dataset not in enabled_ids:
                raise CalibrationError(
                    f"seed sample {sample_id} uses disabled or unknown dataset {source_dataset}"
                )
            kind = sample.get("kind")
            if not isinstance(kind, str):
                raise CalibrationError(f"seed sample {sample_id} has invalid kind")
            counts[kind] = counts.get(kind, 0) + 1

        required: dict[str, int] = {}
        for role_counts in self._ROLE_KINDS.values():
            for kind, count in role_counts.items():
                required[kind] = required.get(kind, 0) + count
        for kind, count in required.items():
            if counts.get(kind, 0) < count:
                raise CalibrationError(
                    f"seed catalog needs {count} disjoint {kind} samples; found {counts.get(kind, 0)}"
                )

        return {
            "status": "VALID",
            "dataset_count": len(datasets),
            "enabled_dataset_count": len(enabled_ids),
            "seed_sample_count": len(samples),
            "registry_sha256": self.registry_sha256,
            "catalog_sha256": self.catalog_sha256,
        }

    @property
    def registry_sha256(self) -> str:
        """Return a stable content hash for the dataset registry."""
        return self._hash(self.registry)

    @property
    def catalog_sha256(self) -> str:
        """Return a stable content hash for the compact structural seed catalog."""
        return self._hash(self.catalog)

    def build_pair(self, *, task_id: str, domain: str) -> dict[str, Any]:
        """Create disjoint writer/reviewer calibration packs for one task."""
        if not task_id.strip():
            raise CalibrationError("task_id must be non-empty")
        domain_tokens = self._tokens(domain)
        writer_samples = self._select_role_samples(
            role="writer",
            task_id=task_id,
            domain_tokens=domain_tokens,
            excluded=set(),
        )
        used = {sample["id"] for sample in writer_samples}
        reviewer_samples = self._select_role_samples(
            role="reviewer",
            task_id=task_id,
            domain_tokens=domain_tokens,
            excluded=used,
        )
        reviewer_ids = {sample["id"] for sample in reviewer_samples}
        overlap = used & reviewer_ids
        if overlap:
            raise CalibrationError(f"writer/reviewer seed overlap: {sorted(overlap)}")

        writer = self._pack("writer", task_id, domain, writer_samples)
        reviewer = self._pack("reviewer", task_id, domain, reviewer_samples)
        pair_identity = {
            "schema_version": self.schema_version,
            "task_id": task_id,
            "domain": domain,
            "registry_sha256": self.registry_sha256,
            "catalog_sha256": self.catalog_sha256,
            "writer_calibration_id": writer["calibration_id"],
            "reviewer_calibration_id": reviewer["calibration_id"],
        }
        return {
            **pair_identity,
            "pair_id": "hwpair-" + self._hash(pair_identity)[:20],
            "independence": {
                "writer_reviewer_seed_overlap": [],
                "status": "PASS",
            },
            "writer": writer,
            "reviewer": reviewer,
        }

    def _pack(
        self,
        role: str,
        task_id: str,
        domain: str,
        samples: list[dict[str, Any]],
    ) -> dict[str, Any]:
        source_ids = [sample["id"] for sample in samples]
        payload = {
            "schema_version": self.schema_version,
            "role": role,
            "task_id": task_id,
            "domain": domain,
            "registry_sha256": self.registry_sha256,
            "catalog_sha256": self.catalog_sha256,
            "local_seed_sample_ids": source_ids,
            "external_sampling": self._external_sampling(role),
            "dataset_weights": self._weights(role),
            "directives": self._directives(role),
        }
        return {
            **payload,
            "calibration_id": f"hwcal-{role}-" + self._hash(payload)[:20],
            "local_seed_samples": samples,
        }

    def _select_role_samples(
        self,
        *,
        role: str,
        task_id: str,
        domain_tokens: set[str],
        excluded: set[str],
    ) -> list[dict[str, Any]]:
        blocked = set(excluded)
        selected: list[dict[str, Any]] = []
        for kind, count in self._ROLE_KINDS[role].items():
            candidates = [
                sample
                for sample in self.catalog["samples"]
                if sample["kind"] == kind and sample["id"] not in blocked
            ]
            ranked = sorted(
                candidates,
                key=lambda sample: self._rank_key(
                    sample,
                    task_id=task_id,
                    role=role,
                    domain_tokens=domain_tokens,
                ),
            )
            if len(ranked) < count:
                raise CalibrationError(
                    f"not enough disjoint {kind} samples for {role}: need {count}"
                )
            chosen = ranked[:count]
            selected.extend(chosen)
            blocked.update(sample["id"] for sample in chosen)
        return selected

    def _rank_key(
        self,
        sample: dict[str, Any],
        *,
        task_id: str,
        role: str,
        domain_tokens: set[str],
    ) -> tuple[int, str]:
        sample_domains = {
            token.lower() for token in sample.get("domains", []) if isinstance(token, str)
        }
        overlap = len(domain_tokens & sample_domains)
        digest = hashlib.sha256(
            f"{task_id}\0{role}\0{sample['id']}".encode("utf-8")
        ).hexdigest()
        return (-overlap, digest)

    def _weights(self, role: str) -> dict[str, float]:
        return {
            dataset["id"]: float(dataset[f"{role}_weight"])
            for dataset in self.registry["datasets"]
            if dataset.get("enabled") is True
        }

    def _external_sampling(self, role: str) -> dict[str, Any]:
        target = self.registry["external_sample_targets"][role]
        eligible = [
            {
                "dataset_id": dataset["id"],
                "source": dataset["source"],
                "license": dataset["license"],
                "purpose": dataset["purpose"],
                "weight": float(dataset[f"{role}_weight"]),
                "content_mode": dataset["content_mode"],
            }
            for dataset in self.registry["datasets"]
            if dataset.get("enabled") is True
            and dataset.get("content_mode") != "local_structural_catalog"
        ]
        return {
            "target": target,
            "eligible_datasets": eligible,
            "required_record_fields": [
                "dataset_id",
                "sample_id_or_source_id",
                "domain_relevance",
                "structural_or_preference_observation",
                "copied_wording=false",
            ],
        }

    @staticmethod
    def _directives(role: str) -> list[str]:
        common = [
            "Learn information selection and constraint preservation, not phrases.",
            "Never add slang, typos, emojis, fake incidents, or invented personal experience to simulate humanity.",
            "Never omit a material requirement for concision or naturalness.",
            "Reference legitimate technical contracts instead of restating them as a hidden-test inventory.",
        ]
        if role == "writer":
            return common + [
                "Draft from the approved solver-visible requirement contract only after calibration is complete.",
                "Use the writer pack only; do not read the reviewer pack or reviewer-only sample IDs.",
            ]
        return common + [
            "Judge completeness before style; a natural but incomplete instruction must fail.",
            "Use the reviewer pack only; do not read the writer pack or writer rationale before fixing an independent verdict.",
            "Treat Human-Like-DPO examples as anti-template contrasts, never as the desired engineering voice.",
        ]

    @staticmethod
    def _tokens(value: str) -> set[str]:
        normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
        return {token for token in normalized.split() if len(token) >= 2}

    @staticmethod
    def _hash(value: Any) -> str:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(rendered).hexdigest()

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CalibrationError(f"cannot load {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise CalibrationError(f"{path} must contain one JSON object")
        return value


def sample_ids(samples: Iterable[dict[str, Any]]) -> set[str]:
    """Return sample IDs from a calibration sample iterable."""
    return {str(sample["id"]) for sample in samples}
