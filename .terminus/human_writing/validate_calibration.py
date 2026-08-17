#!/usr/bin/env python3
"""Fail-closed validator for human-writing stage integration and task calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DEFAULT = Path(__file__).resolve().parents[2]
HW_DIR = Path(__file__).resolve().parent
RETRIEVAL_DIR = HW_DIR.parent / "retrieval"
for entry in (HW_DIR, RETRIEVAL_DIR):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from calibration import HumanWritingCalibrationPlanner  # noqa: E402
from stage_overlay import apply_stage_overlays  # noqa: E402


class CalibrationValidationError(ValueError):
    """Raised when effective stage or task calibration evidence is invalid."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CalibrationValidationError(f"expected JSON object: {path}")
    return value


def validate_effective_stage_contract(root: Path) -> dict[str, Any]:
    registry = _load(root / ".terminus" / "agents" / "stage_contracts.json")
    apply_stage_overlays(root, registry)
    stages = {
        stage["id"]: stage
        for stage in registry.get("stages", [])
        if isinstance(stage, dict) and isinstance(stage.get("id"), str)
    }
    a6 = stages.get("HUMAN_WRITING_RESEARCH")
    a7 = stages.get("INSTRUCTION_DRAFT")
    if not a6 or not a7:
        raise CalibrationValidationError("missing A6/A7 stages")

    expected_statuses = {
        "CALIBRATION_READY",
        "INSUFFICIENT_SOURCE_DIVERSITY",
        "SOURCE_QUALITY_BLOCKED",
        "BLOCKED",
    }
    actual_statuses = set(a6.get("output_contract", {}).get("status_values", []))
    if actual_statuses != expected_statuses:
        raise CalibrationValidationError(
            f"A6 status contract mismatch: {sorted(actual_statuses)}"
        )

    required_output = {
        "DATASET_REGISTRY_SHA256",
        "SEED_CATALOG_SHA256",
        "DOMAIN_PROFILES_SHA256",
        "CALIBRATION_PAIR_ID",
        "WRITER_CALIBRATION_ID",
        "REVIEWER_CALIBRATION_ID",
        "WRITER_REVIEWER_SAMPLE_OVERLAP",
        "EXTERNAL_DATASET_COVERAGE",
        "TASK_WRITING_PROFILE",
    }
    actual_output = set(a6.get("output_contract", {}).get("required_fields", []))
    missing_output = sorted(required_output - actual_output)
    if missing_output:
        raise CalibrationValidationError(
            f"A6 missing hardened output fields: {missing_output}"
        )

    a6_validators = set(a6.get("deterministic_validators", []))
    a7_validators = set(a7.get("deterministic_validators", []))
    validator = ".terminus/human_writing/validate_calibration.py"
    if validator not in a6_validators or validator not in a7_validators:
        raise CalibrationValidationError("calibration validator is not bound to A6/A7")
    a7_inputs = set(a7.get("input_contract", {}).get("required_fields", []))
    if "VALIDATED_HUMAN_WRITING_CALIBRATION" not in a7_inputs:
        raise CalibrationValidationError(
            "INSTRUCTION_DRAFT does not require validated human-writing calibration"
        )
    return {
        "status": "VALID",
        "a6_status_values": sorted(actual_statuses),
        "a6_required_fields": sorted(actual_output),
        "a7_requires_validated_calibration": True,
    }


def validate_pair_and_profile(
    root: Path,
    pair_path: Path,
    profile_path: Path,
) -> dict[str, Any]:
    planner = HumanWritingCalibrationPlanner(root)
    pair = _load(pair_path)
    profile = _load(profile_path)

    expected_hashes = {
        "dataset_registry_sha256": planner.registry_sha256,
        "seed_catalog_sha256": planner.catalog_sha256,
        "domain_profiles_sha256": planner.domain_profiles_sha256,
    }
    for field, expected in expected_hashes.items():
        if pair.get(field) != expected:
            raise CalibrationValidationError(f"stale pair {field}")

    profile_fields = {
        "DATASET_REGISTRY_SHA256": planner.registry_sha256,
        "SEED_CATALOG_SHA256": planner.catalog_sha256,
        "DOMAIN_PROFILES_SHA256": planner.domain_profiles_sha256,
        "CALIBRATION_PAIR_ID": pair.get("pair_id"),
        "WRITER_CALIBRATION_ID": pair.get("writer", {}).get("calibration_id"),
        "REVIEWER_CALIBRATION_ID": pair.get("reviewer", {}).get("calibration_id"),
    }
    for field, expected in profile_fields.items():
        if profile.get(field) != expected:
            raise CalibrationValidationError(f"profile mismatch: {field}")

    writer_ids = set(profile.get("WRITER_SAMPLE_IDS", []))
    reviewer_ids = set(profile.get("REVIEWER_SAMPLE_IDS", []))
    overlap = writer_ids & reviewer_ids
    declared_overlap = profile.get("WRITER_REVIEWER_SAMPLE_OVERLAP")
    if overlap or declared_overlap not in ([], None):
        raise CalibrationValidationError(
            f"writer/reviewer calibration overlap: {sorted(overlap)}"
        )

    writer_sources = set(profile.get("WRITER_EXTERNAL_SOURCE_KEYS", []))
    reviewer_sources = set(profile.get("REVIEWER_EXTERNAL_SOURCE_KEYS", []))
    source_overlap = writer_sources & reviewer_sources
    if source_overlap:
        raise CalibrationValidationError(
            f"writer/reviewer external source overlap: {sorted(source_overlap)}"
        )

    coverage = profile.get("EXTERNAL_DATASET_COVERAGE")
    if coverage not in {"FULL", "DEGRADED"}:
        raise CalibrationValidationError("external coverage must be FULL or DEGRADED")
    if coverage == "DEGRADED":
        approval = profile.get("DEGRADED_COVERAGE_APPROVAL")
        if not isinstance(approval, dict) or approval.get("approved") is not True:
            raise CalibrationValidationError(
                "DEGRADED coverage requires an explicit controller approval"
            )
        if not approval.get("approved_by") or not approval.get("reason"):
            raise CalibrationValidationError(
                "degraded-coverage approval requires approved_by and reason"
            )

    cache_keys = set(profile.get("CACHE_SOURCE_KEYS_USED", []))
    raw_keys = set(profile.get("RAW_SOURCE_KEYS_USED_FOR_CONTAMINATION", []))
    if not raw_keys.issubset(cache_keys):
        raise CalibrationValidationError(
            "contamination source keys must be a subset of cache source keys"
        )

    return {
        "status": "VALID",
        "pair_id": pair.get("pair_id"),
        "coverage": coverage,
        "writer_sample_count": len(writer_ids),
        "reviewer_sample_count": len(reviewer_ids),
        "external_source_overlap": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT_DEFAULT))
    parser.add_argument("--pair")
    parser.add_argument("--profile")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    result: dict[str, Any] = {
        "effective_stage_contract": validate_effective_stage_contract(root),
        "planner": HumanWritingCalibrationPlanner(root).validate(),
    }
    if bool(args.pair) != bool(args.profile):
        raise CalibrationValidationError("--pair and --profile must be supplied together")
    if args.pair:
        result["task_calibration"] = validate_pair_and_profile(
            root,
            Path(args.pair).resolve(),
            Path(args.profile).resolve(),
        )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
