#!/usr/bin/env python3
"""Validate Terminus retrieval metadata/indexing contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
AGENTS = T / "agents"

METADATA_PATH = AGENTS / "retrieval_metadata.json"
POLICY_PATH = AGENTS / "RETRIEVAL_METADATA.md"
CHUNK_SCHEMA_PATH = AGENTS / "schemas" / "retrieval_chunk.schema.json"
MANIFEST_SCHEMA_PATH = AGENTS / "schemas" / "retrieval_manifest.schema.json"
VISIBILITY_PATH = AGENTS / "evidence_visibility.json"
STAGES_PATH = AGENTS / "stage_contracts.json"

EXPECTED_SOURCE_KINDS = {
    "CONTROL_PLANE_MARKDOWN",
    "CONTROL_PLANE_JSON",
    "CONTROL_PLANE_CODE",
    "TASK_INSTRUCTION",
    "TASK_DOCUMENTATION",
    "TASK_CODE",
    "TASK_CONFIGURATION",
    "PRIVATE_DESIGN",
    "SOLUTION_ORACLE",
    "VERIFIER_PRIVATE",
    "REVIEW_PACKET",
    "REVIEW_RESULT",
    "SESSION_STATE",
    "CI_RUNTIME",
    "MODEL_TRIAL",
    "FINAL_PACKAGE",
    "PUBLIC_REFERENCE",
}

EXPECTED_FRESHNESS = {
    "CONTENT_HASH",
    "GIT_BLOB_SHA",
    "TASK_COMMIT",
    "CONTROL_PLANE_COMMIT",
    "POLICY_VERSION",
    "ROLE_CONTRACT_HASH",
    "PACKET_BINDING",
    "REVIEW_SCOPE_HASH",
    "CI_RUN_ID",
    "EXTERNAL_CONTENT_HASH",
}

EXPECTED_SENSITIVITY = {
    "PUBLIC",
    "SOLVER_VISIBLE",
    "CONTROL_PLANE",
    "PRIVATE",
    "RESTRICTED",
}

POLICY_MARKERS = [
    "Retrieval metadata policy version: `1.0`",
    "stage/role/packet authority",
    "evidence visibility filter",
    "freshness/provenance filter",
    "document_id",
    "chunk_id",
    "Chunking policy",
    "Freshness scopes",
    "Retrieval filtering contract",
    "Caching implication",
    "Anti-leakage invariants",
]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def load_json(path: Path, errors: list[str]) -> object:
    if not path.is_file():
        fail(errors, f"missing required file: {path.relative_to(ROOT)}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(errors, f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return {}


def main() -> int:
    errors: list[str] = []

    metadata = load_json(METADATA_PATH, errors)
    chunk_schema = load_json(CHUNK_SCHEMA_PATH, errors)
    manifest_schema = load_json(MANIFEST_SCHEMA_PATH, errors)
    visibility = load_json(VISIBILITY_PATH, errors)
    stages = load_json(STAGES_PATH, errors)

    if not POLICY_PATH.is_file():
        fail(errors, f"missing required file: {POLICY_PATH.relative_to(ROOT)}")
        policy = ""
    else:
        policy = POLICY_PATH.read_text(encoding="utf-8")
    for marker in POLICY_MARKERS:
        if marker.lower() not in policy.lower():
            fail(errors, f"{POLICY_PATH.relative_to(ROOT)} missing required marker: {marker}")

    if not isinstance(metadata, dict):
        fail(errors, "retrieval metadata registry must be an object")
        metadata = {}
    if metadata.get("metadata_contract_version") != "1.0":
        fail(errors, "retrieval metadata contract must declare version 1.0")

    source_kinds = set(metadata.get("source_kinds", [])) if isinstance(metadata.get("source_kinds"), list) else set()
    if source_kinds != EXPECTED_SOURCE_KINDS:
        fail(errors, f"source kind set mismatch missing={sorted(EXPECTED_SOURCE_KINDS-source_kinds)} extra={sorted(source_kinds-EXPECTED_SOURCE_KINDS)}")

    freshness = set(metadata.get("freshness_scopes", [])) if isinstance(metadata.get("freshness_scopes"), list) else set()
    if freshness != EXPECTED_FRESHNESS:
        fail(errors, f"freshness scope set mismatch missing={sorted(EXPECTED_FRESHNESS-freshness)} extra={sorted(freshness-EXPECTED_FRESHNESS)}")

    sensitivity = set(metadata.get("sensitivity_values", [])) if isinstance(metadata.get("sensitivity_values"), list) else set()
    if sensitivity != EXPECTED_SENSITIVITY:
        fail(errors, f"sensitivity set mismatch missing={sorted(EXPECTED_SENSITIVITY-sensitivity)} extra={sorted(sensitivity-EXPECTED_SENSITIVITY)}")

    visibility_classes: set[str] = set()
    visibility_version = "?"
    if isinstance(visibility, dict):
        visibility_version = str(visibility.get("visibility_version", "?"))
        declared = visibility.get("evidence_classes", {})
        if isinstance(declared, dict):
            visibility_classes = set(declared)
    if visibility_version != "1.1":
        fail(errors, "retrieval metadata requires evidence visibility version 1.1")

    stage_ids: set[str] = set()
    if isinstance(stages, dict):
        stage_list = stages.get("stages", [])
        if isinstance(stage_list, list):
            for stage in stage_list:
                if isinstance(stage, dict) and isinstance(stage.get("id"), str):
                    stage_ids.add(stage["id"])
    if not stage_ids:
        fail(errors, "could not resolve registered stage IDs")

    profiles = metadata.get("source_profiles", {})
    if not isinstance(profiles, dict):
        fail(errors, "source_profiles must be an object")
        profiles = {}
    if set(profiles) != EXPECTED_SOURCE_KINDS:
        fail(errors, "source_profiles must have one profile for every source kind")

    for source_kind, profile in profiles.items():
        if not isinstance(profile, dict):
            fail(errors, f"{source_kind}: source profile must be an object")
            continue
        evidence_class = profile.get("default_evidence_class")
        if evidence_class not in visibility_classes:
            fail(errors, f"{source_kind}: unknown evidence class {evidence_class!r}")
        sensitivity_value = profile.get("default_sensitivity")
        if sensitivity_value not in EXPECTED_SENSITIVITY:
            fail(errors, f"{source_kind}: invalid sensitivity {sensitivity_value!r}")
        required_freshness = profile.get("required_freshness", [])
        if not isinstance(required_freshness, list) or not required_freshness:
            fail(errors, f"{source_kind}: required_freshness must be a non-empty list")
        else:
            unknown = set(required_freshness) - EXPECTED_FRESHNESS
            if unknown:
                fail(errors, f"{source_kind}: unknown freshness scopes {sorted(unknown)}")

    required_fields = set(metadata.get("required_chunk_fields", [])) if isinstance(metadata.get("required_chunk_fields"), list) else set()
    for field in {
        "document_id",
        "chunk_id",
        "source_uri",
        "source_kind",
        "source_version",
        "content_hash",
        "evidence_class",
        "sensitivity",
        "solver_visible",
        "stage_applicability",
        "role_applicability",
        "freshness_scope",
        "chunk_type",
        "structural_locator",
        "ordinal",
    }:
        if field not in required_fields:
            fail(errors, f"required_chunk_fields missing {field}")

    if isinstance(chunk_schema, dict):
        if chunk_schema.get("$id") != "terminus-retrieval-chunk-v1":
            fail(errors, "retrieval chunk schema must declare $id terminus-retrieval-chunk-v1")
        if chunk_schema.get("additionalProperties") is not False:
            fail(errors, "retrieval chunk schema must reject undeclared fields")
        properties = chunk_schema.get("properties", {})
        if isinstance(properties, dict):
            source_enum = set(properties.get("source_kind", {}).get("enum", [])) if isinstance(properties.get("source_kind"), dict) else set()
            if source_enum != EXPECTED_SOURCE_KINDS:
                fail(errors, "retrieval chunk source_kind enum must match registry")
            evidence_enum = set(properties.get("evidence_class", {}).get("enum", [])) if isinstance(properties.get("evidence_class"), dict) else set()
            if evidence_enum != visibility_classes:
                fail(errors, "retrieval chunk evidence_class enum must match evidence visibility registry")
            freshness_enum = set(properties.get("freshness_scope", {}).get("items", {}).get("enum", [])) if isinstance(properties.get("freshness_scope"), dict) else set()
            if freshness_enum != EXPECTED_FRESHNESS:
                fail(errors, "retrieval chunk freshness_scope enum must match metadata registry")

    if isinstance(manifest_schema, dict):
        if manifest_schema.get("$id") != "terminus-retrieval-manifest-v1":
            fail(errors, "retrieval manifest schema must declare $id terminus-retrieval-manifest-v1")
        properties = manifest_schema.get("properties", {})
        if isinstance(properties, dict):
            visibility_const = properties.get("evidence_visibility_version", {}).get("const") if isinstance(properties.get("evidence_visibility_version"), dict) else None
            if visibility_const != "1.1":
                fail(errors, "retrieval manifest must bind evidence visibility version 1.1")

    global_tokens = metadata.get("global_applicability_tokens", {})
    if not isinstance(global_tokens, dict) or global_tokens.get("stage") != "ALL_AUTHORIZED_STAGES" or global_tokens.get("role") != "ALL_AUTHORIZED_ROLES":
        fail(errors, "global applicability tokens are missing or invalid")

    # Critical mappings that must remain conservative.
    expected_profile_classes = {
        "TASK_INSTRUCTION": "SOLVER_VISIBLE_TASK",
        "TASK_DOCUMENTATION": "SOLVER_VISIBLE_TASK",
        "TASK_CODE": "SOLVER_VISIBLE_TASK",
        "SOLUTION_ORACLE": "SOLUTION_ORACLE",
        "VERIFIER_PRIVATE": "VERIFIER_PRIVATE",
        "PRIVATE_DESIGN": "PRIVATE_CREATION_DESIGN",
        "REVIEW_PACKET": "CURRENT_REVIEW_PACKET",
        "REVIEW_RESULT": "PRIOR_REVIEW_RESULTS",
    }
    for source_kind, expected_class in expected_profile_classes.items():
        profile = profiles.get(source_kind, {})
        if isinstance(profile, dict) and profile.get("default_evidence_class") != expected_class:
            fail(errors, f"{source_kind}: expected evidence class {expected_class}")

    if errors:
        print("Terminus retrieval metadata validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Terminus retrieval metadata validation PASS")
    print(
        f"metadata_contract=1.0 visibility={visibility_version} "
        f"source_kinds={len(source_kinds)} evidence_classes={len(visibility_classes)} "
        f"registered_stages={len(stage_ids)} freshness_scopes={len(freshness)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
