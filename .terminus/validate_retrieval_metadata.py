#!/usr/bin/env python3
"""Validate Terminus retrieval metadata/indexing contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
AGENTS = T / "agents"

METADATA_PATH = AGENTS / "retrieval_metadata.json"
POLICY_PATH = AGENTS / "RETRIEVAL_METADATA.md"
CHUNK_SCHEMA_PATH = AGENTS / "schemas" / "retrieval_chunk.schema.json"
MANIFEST_SCHEMA_PATH = AGENTS / "schemas" / "retrieval_manifest.schema.json"
VISIBILITY_PATH = AGENTS / "evidence_visibility.json"
STAGES_PATH = AGENTS / "stage_contracts.json"
REQUIREMENT_SCHEMA_PATH = AGENTS / "schemas" / "solver_visible_requirement_contract.schema.json"
INDEXER_PATH = T / "retrieval" / "indexer.py"

EXPECTED_FRESHNESS_BINDINGS = {
    "GIT_BLOB_SHA": "git_blob_sha",
    "TASK_COMMIT": "task_commit",
    "CONTROL_PLANE_COMMIT": "control_plane_commit",
    "POLICY_VERSION": "policy_versions",
    "ROLE_CONTRACT_HASH": "role_contract_hash",
    "PACKET_BINDING": "packet_binding",
    "REVIEW_SCOPE_HASH": "review_scope_hash",
    "CI_RUN_ID": "ci_run_id",
}
PRIVATE_KINDS = {
    "PRIVATE_WORK_PACKAGE_DESIGN",
    "PRIVATE_SYSTEM_ARCHITECTURE",
    "PRIVATE_DEFECT_TOPOLOGY",
    "PRIVATE_TEST_MAP",
}
POLICY_MARKERS = [
    "Retrieval metadata policy version: `1.0`",
    "fail closed",
    "stage/role/packet authority",
    "evidence visibility filter",
    "freshness/provenance filter",
    "canonical role IDs",
    "Source-profile constraints",
    "Anti-leakage invariants",
]


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing required file: {path.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(ROOT)} must contain one object")
        return {}
    return value


def as_string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


def source_conditions(schema: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for item in schema.get("allOf", []):
        if not isinstance(item, dict):
            continue
        condition = item.get("if", {})
        try:
            source = condition["properties"]["source_kind"]
        except (KeyError, TypeError):
            continue
        if not isinstance(source, dict):
            continue
        value = source.get("const")
        if isinstance(value, str):
            found.add(value)
        found.update(as_string_set(source.get("enum")))
    return found


def validate_chunk_semantics(
    chunk: dict[str, Any],
    metadata: dict[str, Any],
    stage_ids: set[str],
    role_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    kind = chunk.get("source_kind")
    profiles = metadata.get("source_profiles", {})
    if not isinstance(kind, str) or not isinstance(profiles, dict):
        return ["chunk has no valid source_kind/source_profiles"]
    profile = profiles.get(kind)
    if not isinstance(profile, dict):
        return [f"unknown source profile {kind!r}"]
    for field, expected in {
        "evidence_class": profile.get("default_evidence_class"),
        "sensitivity": profile.get("default_sensitivity"),
        "solver_visible": profile.get("default_solver_visible"),
    }.items():
        if chunk.get(field) != expected:
            errors.append(f"{kind}: {field} must be {expected!r}")
    for field in as_string_set(profile.get("required_bindings")):
        if chunk.get(field) in (None, "", [], {}):
            errors.append(f"{kind}: required binding {field} is missing")
    freshness = as_string_set(chunk.get("freshness_scope"))
    missing = as_string_set(profile.get("required_freshness")) - freshness
    if missing:
        errors.append(f"{kind}: missing freshness {sorted(missing)}")
    stage_values = as_string_set(chunk.get("stage_applicability"))
    if stage_values - (stage_ids | {"ALL_AUTHORIZED_STAGES"}):
        errors.append("unknown stage applicability")
    if "ALL_AUTHORIZED_STAGES" in stage_values and len(stage_values) != 1:
        errors.append("ALL_AUTHORIZED_STAGES must be exclusive")
    role_values = as_string_set(chunk.get("role_applicability"))
    if role_values - (role_ids | {"ALL_AUTHORIZED_ROLES"}):
        errors.append("unknown role applicability")
    if "ALL_AUTHORIZED_ROLES" in role_values and len(role_values) != 1:
        errors.append("ALL_AUTHORIZED_ROLES must be exclusive")
    return errors


def main() -> int:
    errors: list[str] = []
    metadata = load_json(METADATA_PATH, errors)
    chunk_schema = load_json(CHUNK_SCHEMA_PATH, errors)
    manifest_schema = load_json(MANIFEST_SCHEMA_PATH, errors)
    visibility = load_json(VISIBILITY_PATH, errors)
    stages = load_json(STAGES_PATH, errors)
    requirement_schema = load_json(REQUIREMENT_SCHEMA_PATH, errors)

    policy_text = POLICY_PATH.read_text(encoding="utf-8") if POLICY_PATH.is_file() else ""
    for marker in POLICY_MARKERS:
        if marker.lower() not in policy_text.lower():
            errors.append(f"RETRIEVAL_METADATA.md missing marker: {marker}")

    if metadata.get("metadata_contract_version") != "1.0":
        errors.append("metadata contract version must be 1.0")
    if visibility.get("visibility_version") != "1.1":
        errors.append("evidence visibility version must be 1.1")

    source_kinds = as_string_set(metadata.get("source_kinds"))
    role_ids = as_string_set(metadata.get("canonical_role_ids"))
    freshness_scopes = as_string_set(metadata.get("freshness_scopes"))
    sensitivity_values = as_string_set(metadata.get("sensitivity_values"))
    if not source_kinds or len(source_kinds) != len(metadata.get("source_kinds", [])):
        errors.append("source_kinds must be a non-empty unique string list")
    if not role_ids or len(role_ids) != len(metadata.get("canonical_role_ids", [])):
        errors.append("canonical_role_ids must be a non-empty unique string list")
    if not freshness_scopes:
        errors.append("freshness_scopes must be non-empty")

    stage_ids = {
        stage.get("id")
        for stage in stages.get("stages", [])
        if isinstance(stage, dict) and isinstance(stage.get("id"), str)
    }
    visibility_stage_ids = {
        stage.get("stage_id")
        for stage in visibility.get("stages", [])
        if isinstance(stage, dict) and isinstance(stage.get("stage_id"), str)
    }
    if stage_ids != visibility_stage_ids:
        errors.append(
            f"stage/visibility coverage mismatch missing={sorted(stage_ids-visibility_stage_ids)} "
            f"extra={sorted(visibility_stage_ids-stage_ids)}"
        )

    aliases = metadata.get("role_aliases")
    if not isinstance(aliases, dict) or not aliases:
        errors.append("role_aliases must be a non-empty object")
    elif set(aliases.values()) - role_ids:
        errors.append("role_aliases contains noncanonical role IDs")
    if metadata.get("freshness_binding_fields") != EXPECTED_FRESHNESS_BINDINGS:
        errors.append("freshness_binding_fields drift")

    profiles = metadata.get("source_profiles")
    if not isinstance(profiles, dict) or set(profiles) != source_kinds:
        errors.append("source_profiles must cover every source kind exactly")
        profiles = {} if not isinstance(profiles, dict) else profiles
    required_profile_keys = {
        "default_evidence_class","default_sensitivity","default_solver_visible",
        "repository_backed","task_scoped","chunk_strategy","required_bindings","required_freshness",
    }
    evidence_classes = set(visibility.get("evidence_classes", {}))
    chunk_types = as_string_set(metadata.get("chunk_types"))
    for kind, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(f"{kind}: source profile must be an object")
            continue
        if set(profile) != required_profile_keys:
            errors.append(f"{kind}: source profile key set drift")
        if profile.get("default_evidence_class") not in evidence_classes:
            errors.append(f"{kind}: unknown evidence class")
        if profile.get("default_sensitivity") not in sensitivity_values:
            errors.append(f"{kind}: unknown sensitivity")
        if not isinstance(profile.get("default_solver_visible"), bool):
            errors.append(f"{kind}: solver_visible must be boolean")
        if profile.get("chunk_strategy") not in chunk_types:
            errors.append(f"{kind}: invalid chunk strategy")
        bindings = as_string_set(profile.get("required_bindings"))
        fresh = as_string_set(profile.get("required_freshness"))
        if not fresh or not fresh <= freshness_scopes:
            errors.append(f"{kind}: invalid required freshness")
        if profile.get("repository_backed") is True and not {"source_path","git_blob_sha"} <= bindings:
            errors.append(f"{kind}: repository-backed source missing path/blob bindings")
        if profile.get("task_scoped") is True and not {"task_id","task_commit"} <= bindings:
            errors.append(f"{kind}: task-scoped source missing task bindings")
        for scope in fresh:
            field = EXPECTED_FRESHNESS_BINDINGS.get(scope)
            if field and field not in bindings:
                errors.append(f"{kind}: {scope} requires binding {field}")

    for kind in PRIVATE_KINDS:
        profile = profiles.get(kind, {})
        if (
            profile.get("default_evidence_class") != "PRIVATE_CREATION_DESIGN"
            or profile.get("default_sensitivity") != "PRIVATE"
            or profile.get("default_solver_visible") is not False
        ):
            errors.append(f"{kind}: private-design mapping must fail closed")
    result_profile = profiles.get("REVIEW_RESULT", {})
    if (
        result_profile.get("default_evidence_class") != "CURRENT_REVIEW_PACKET"
        or result_profile.get("default_sensitivity") != "CONTROL_PLANE"
        or result_profile.get("default_solver_visible") is not False
        or not {"task_id","task_commit","control_plane_commit","role_contract_hash","packet_binding"}
        <= as_string_set(result_profile.get("required_bindings"))
    ):
        errors.append("REVIEW_RESULT must be current, freshness-bound review evidence")
    if "HARBOR_LLMAJ_GATE" not in role_ids:
        errors.append("canonical roles must include HARBOR_LLMAJ_GATE")

    properties = chunk_schema.get("properties", {})
    source_enum = as_string_set(properties.get("source_kind", {}).get("enum", []))
    stage_enum = as_string_set(properties.get("stage_applicability", {}).get("items", {}).get("enum", []))
    role_enum = as_string_set(properties.get("role_applicability", {}).get("items", {}).get("enum", []))
    evidence_enum = as_string_set(properties.get("evidence_class", {}).get("enum", []))
    if source_enum != source_kinds:
        errors.append("retrieval chunk source_kind enum must match registry")
    if stage_enum != stage_ids | {"ALL_AUTHORIZED_STAGES"}:
        errors.append("retrieval chunk stage_applicability enum must match registered stages")
    if role_enum != role_ids | {"ALL_AUTHORIZED_ROLES"}:
        errors.append("retrieval chunk role_applicability enum must match canonical roles")
    if evidence_enum != evidence_classes:
        errors.append("retrieval chunk evidence_class enum must match visibility classes")
    if source_conditions(chunk_schema) != source_kinds:
        errors.append("retrieval chunk schema must constrain every source kind")

    manifest_properties = manifest_schema.get("properties", {})
    manifest_sources = as_string_set(manifest_properties.get("source_kind_counts", {}).get("propertyNames", {}).get("enum", []))
    manifest_evidence = as_string_set(manifest_properties.get("evidence_class_counts", {}).get("propertyNames", {}).get("enum", []))
    manifest_roles = as_string_set(manifest_properties.get("role_contract_hashes", {}).get("propertyNames", {}).get("enum", []))
    if manifest_sources != source_kinds:
        errors.append("retrieval manifest source kinds must match registry")
    if manifest_evidence != evidence_classes:
        errors.append("retrieval manifest evidence classes must match visibility")
    if manifest_roles != role_ids:
        errors.append("retrieval manifest role IDs must match registry")

    private_excluded = requirement_schema.get("properties", {}).get("private_sources_excluded", {})
    if private_excluded.get("const") is not True:
        errors.append("solver-visible requirement contract must require private_sources_excluded=true")

    indexer = INDEXER_PATH.read_text(encoding="utf-8") if INDEXER_PATH.is_file() else ""
    for marker in PRIVATE_KINDS | {"_PRIVATE_DESIGN_STAGE_APPLICABILITY", "return None"}:
        if marker not in indexer:
            errors.append(f"retrieval indexer missing private-design fail-closed marker {marker}")

    # Semantic self-tests exercise the registry rather than trusting schema text alone.
    instruction = profiles.get("TASK_INSTRUCTION", {})
    if instruction:
        valid = {
            "source_kind":"TASK_INSTRUCTION","evidence_class":"SOLVER_VISIBLE_TASK",
            "sensitivity":"SOLVER_VISIBLE","solver_visible":True,
            "source_path":"task/instruction.md","git_blob_sha":"a"*40,
            "task_id":"task","task_commit":"b"*40,
            "freshness_scope":["GIT_BLOB_SHA","TASK_COMMIT"],
            "stage_applicability":["ALL_AUTHORIZED_STAGES"],"role_applicability":["ALL_AUTHORIZED_ROLES"],
        }
        if validate_chunk_semantics(valid, metadata, stage_ids, role_ids):
            errors.append("valid TASK_INSTRUCTION self-test failed")
        forged = dict(valid)
        forged.update({"source_kind":"SOLUTION_ORACLE","evidence_class":"SOLVER_VISIBLE_TASK","solver_visible":True})
        if not validate_chunk_semantics(forged, metadata, stage_ids, role_ids):
            errors.append("Oracle mislabeled as solver-visible did not fail closed")

    if errors:
        print("Terminus retrieval metadata validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Terminus retrieval metadata validation PASS")
    print(
        "metadata_contract=1.0 "
        f"visibility={visibility.get('visibility_version')} "
        f"source_kinds={len(source_kinds)} evidence_classes={len(evidence_classes)} "
        f"registered_stages={len(stage_ids)} canonical_roles={len(role_ids)} "
        f"freshness_scopes={len(freshness_scopes)} fail_closed=enabled"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
