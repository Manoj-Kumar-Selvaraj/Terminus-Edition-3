"""Reproducible materialization of approved external dataset snapshots into the cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from corpus_cache import HumanWritingCorpusCache, CorpusCacheError


class MaterializationError(ValueError):
    """Raised when a source snapshot cannot be materialized reproducibly."""


class CorpusMaterializer:
    """Build the local cache from a normalized, revision-bound JSONL snapshot."""

    schema_version = "1.0"

    def __init__(self, root: Path, cache_path: Path | None = None):
        self.root = root.resolve()
        self.cache = HumanWritingCorpusCache(self.root, cache_path)
        self.registry = self.cache.registry
        self.datasets = self.cache.datasets

    def materialize(
        self,
        *,
        dataset_id: str,
        input_path: Path,
        source_revision: str,
        role_signal: str,
        limit: int | None = None,
    ) -> dict[str, Any]:
        dataset = self.datasets.get(dataset_id)
        if not dataset or dataset.get("enabled") is not True:
            raise MaterializationError(f"dataset disabled or unknown: {dataset_id}")
        if dataset.get("content_mode") != "external_retrieval_or_local_cache":
            raise MaterializationError(f"dataset is not externally materializable: {dataset_id}")
        if not source_revision.strip():
            raise MaterializationError("source_revision is required")
        requested_roles = {"writer", "reviewer"} if role_signal == "both" else {role_signal}
        if not requested_roles <= set(dataset.get("allowed_roles", [])):
            raise MaterializationError(
                f"dataset {dataset_id} is not allowed for roles {sorted(requested_roles)}"
            )
        if limit is not None and limit <= 0:
            raise MaterializationError("limit must be positive")
        raw = input_path.read_bytes()
        input_sha256 = hashlib.sha256(raw).hexdigest()
        count = 0
        source_ids: list[str] = []
        for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            if limit is not None and count >= limit:
                break
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MaterializationError(f"invalid JSONL line {line_no}: {exc}") from exc
            if not isinstance(record, dict):
                raise MaterializationError(f"JSONL line {line_no} is not an object")
            supplied_dataset = record.get("dataset_id")
            if supplied_dataset not in {None, dataset_id}:
                raise MaterializationError(
                    f"line {line_no} dataset_id conflicts with requested dataset"
                )
            supplied_revision = record.get("source_revision")
            if supplied_revision not in {None, source_revision}:
                raise MaterializationError(
                    f"line {line_no} source_revision conflicts with requested revision"
                )
            supplied_role = record.get("role_signal")
            if supplied_role not in {None, role_signal}:
                raise MaterializationError(
                    f"line {line_no} role_signal conflicts with requested role"
                )
            normalized = {
                **record,
                "dataset_id": dataset_id,
                "source_revision": source_revision,
                "role_signal": role_signal,
            }
            try:
                self.cache.upsert(normalized)
            except CorpusCacheError as exc:
                raise MaterializationError(f"line {line_no}: {exc}") from exc
            count += 1
            source_ids.append(str(normalized["source_id"]))

        manifest = {
            "schema_version": self.schema_version,
            "dataset_id": dataset_id,
            "source_revision": source_revision,
            "role_signal": role_signal,
            "input_path_name": input_path.name,
            "input_sha256": input_sha256,
            "record_count": count,
            "source_ids_sha256": hashlib.sha256(
                json.dumps(sorted(source_ids), separators=(",", ":")).encode()
            ).hexdigest(),
            "cache_schema_version": self.cache.schema_version,
            "registry_schema_version": self.registry.get("schema_version"),
            "cache_stats": self.cache.stats(),
        }
        manifest["materialization_id"] = "hwmat-" + hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:20]
        path = (
            self.root
            / ".terminus"
            / "cache"
            / "human-writing-materializations"
            / f"{manifest['materialization_id']}.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest
