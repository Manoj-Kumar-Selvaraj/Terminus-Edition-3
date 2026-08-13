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
REQUIREMENT_SCHEMA_PATH = AGENTS / "schemas" / "solver_visible_requirement_contract.schema.json"

EXPECTED_SOURCE_KINDS = {
    "CONTROL_PLANE_MARKDOWN",
    "CONTROL_PLANE_JSON",
    "CONTROL_PLANE_CODE",
    "TASK_INSTRUCTION",
    "TASK_DOCUMENTATION",
    "TASK_CODE",
    "TASK_CONFIGURATION",
    "SOLVER_VISIBLE_REQUIREMENT_CONTRACT",
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

EXPECTED_ROLE_IDS = {
    "CREATION_CONTROLLER",
    "CI_ORCHESTRATOR",
    "A1_SCENARIO_RESEARCHER",
    "A2_SYSTEM_ARCHITECT",
    "A2_ENVIRONMENT_BUILDER",
    "A3_DEFECT_TOPOLOGY_DESIGNER",
    "A4_REFERENCE_SOLUTION_AUTHOR",
    "A5_VERIFIER_AUTHOR",
    "A6_HUMAN_WRITING_RESEARCHER",
    "A7_INSTRUCTION_WRITER",
    "A8_DOCUMENTATION_WRITER",
    "A9_TASK_ASSEMBLY_AGENT",
    "A10_COMPLEXITY_GOVERNOR",
    "A11_AUTHORING_FAILURE_DIAGNOSTICIAN",
    "Q1_SPEC_GAP_REPAIRER",
    "Q2_VERIFIER_COVERAGE_REPAIRER",
    "Q3_SPEC_AMBIGUITY_REPAIRER",
    "Q4_SPEC_TEST_CONTRACT_REVIEWER",
    "Q5_ORACLE_RUNTIME_REPAIR_SPECIALIST",
    "Q6_PRODUCTION_LOGIC_AUDITOR",
    "Q7_TASK_FORMAT_ENFORCER",
    "Q8_MODEL_PERSPECTIVE_DIFFICULTY_SIMULATOR",
    "TASK_ARCHITECT",
    "ORIGINALITY_AUTHENTICITY_REVIEWER",
    "VERIFIER_ENGINEER",
    "HUMAN_QUALITY_REVIEWER",
    "INSTRUCTION_REVIEWER",
    "ENGINEERING_DOCUMENTATION_REVIEWER",
    "COMPLIANCE_AUDITOR",
    "COMPREHENSIVE_REVIEWER",
    "ADJUDICATOR",
    "DIFFICULTY_REVIEWER",
    "TRAJECTORY_ANALYST",
    "OFFICIAL_MODEL_EVALUATION_GATE",
}

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

POLICY_MARKERS = [
    "Retrieval metadata policy version: `1.0`",
    "fail closed",
    "stage/role/packet authority",
    "evidence visibility filter",
    "freshness/provenance filter",
    "document_id",
    "chunk_id",
    "canonical role IDs",
    "Source-profile constraints",
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


def _set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


def validate_chunk_semantics(
    chunk: dict[str, object],
    metadata: dict[str, object],
    stage_ids: set[str],
    role_ids: set[str],
) -> list[str]:
    """Return semantic metadata errors for one already-parsed chunk."""
    errors: list[str] = []
    source_kind = chunk.get("source_kind")
    profiles = metadata.get("source_profiles", {})
    if not isinstance(source_kind, str) or not isinstance(profiles, dict):
        return ["chunk has no valid source_kind/source_profiles"]
    profile = profiles.get(source_kind)
    if not isinstance(profile, dict):
        return [f"unknown source profile {source_kind!r}"]

    expected_pairs = {
        "evidence_class": profile.get("default_evidence_class"),
        "sensitivity": profile.get("default_sensitivity"),
        "solver_visible": profile.get("default_solver_visible"),
    }
    for field, expected in expected_pairs.items():
        if chunk.get(field) != expected:
            errors.append(f"{source_kind}: {field} must be {expected!r}")

    required_bindings = _set(profile.get("required_bindings"))
    for field in required_bindings:
        value = chunk.get(field)
        if value is None or value == "" or value == [] or value == {}:
            errors.append(f"{source_kind}: required binding {field} is missing")

    freshness = _set(chunk.get("freshness_scope"))
    required_freshness = _set(profile.get("required_freshness"))
    missing_freshness = required_freshness - freshness
    if missing_freshness:
        errors.append(f"{source_kind}: missing required freshness scopes {sorted(missing_freshness)}")

    freshness_bindings = metadata.get("freshness_binding_fields", {})
    if isinstance(freshness_bindings, dict):
        for scope in freshness:
            field = freshness_bindings.get(scope)
            if isinstance(field, str):
                value = chunk.get(field)
                if value is None or value == "" or value == [] or value == {}:
                    errors.append(f"{source_kind}: freshness scope {scope} requires binding {field}")

    if profile.get("repository_backed") is True:
        for field in ("source_path", "git_blob_sha"):
            if not chunk.get(field):
                errors.append(f"{source_kind}: repository-backed source requires {field}")
    if profile.get("task_scoped") is True:
        for field in ("task_id", "task_commit"):
            if not chunk.get(field):
                errors.append(f"{source_kind}: task-scoped source requires {field}")

    stage_values = _set(chunk.get("stage_applicability"))
    allowed_stages = stage_ids | {"ALL_AUTHORIZED_STAGES"}
    unknown_stages = stage_values - allowed_stages
    if unknown_stages:
        errors.append(f"unknown stage applicability {sorted(unknown_stages)}")
    if "ALL_AUTHORIZED_STAGES" in stage_values and len(stage_values) != 1:
        errors.append("ALL_AUTHORIZED_STAGES must be the only stage applicability token")

    role_values = _set(chunk.get("role_applicability"))
    allowed_roles = role_ids | {"ALL_AUTHORIZED_ROLES"}
    unknown_roles = role_values - allowed_roles
    if unknown_roles:
        errors.append(f"unknown role applicability {sorted(unknown_roles)}")
    if "ALL_AUTHORIZED_ROLES" in role_values and len(role_values) != 1:
        errors.append("ALL_AUTHORIZED_ROLES must be the only role applicability token")

    return errors


def main() -> int:
    errors: list[str] = []

    metadata_raw = load_json(METADATA_PATH, errors)
    chunk_schema = load_json(CHUNK_SCHEMA_PATH, errors)
    manifest_schema = load_json(MANIFEST_SCHEMA_PATH, errors)
    requirement_schema = load_json(REQUIREMENT_SCHEMA_PATH, errors)
    visibility = load_json(VISIBILITY_PATH, errors)
    stages = load_json(STAGES_PATH, errors)

    metadata = metadata_raw if isinstance(metadata_raw, dict) else {}
    if not isinstance(metadata_raw, dict):
        fail(errors, "retrieval metadata registry must be an object")

    policy = POLICY_PATH.read_text(encoding="utf-8") if POLICY_PATH.is_file() else ""
    if not POLICY_PATH.is_file():
        fail(errors, f"missing required file: {POLICY_PATH.relative_to(ROOT)}")
    for marker in POLICY_MARKERS:
        if marker.lower() not in policy.lower():
            fail(errors, f"{POLICY_PATH.relative_to(ROOT)} missing required marker: {marker}")

    if metadata.get("metadata_contract_version") != "1.0":
        fail(errors, "retrieval metadata contract must declare version 1.0")

    source_kinds = _set(metadata.get("source_kinds"))
    if source_kinds != EXPECTED_SOURCE_KINDS:
        fail(errors, f"source kind set mismatch missing={sorted(EXPECTED_SOURCE_KINDS-source_kinds)} extra={sorted(source_kinds-EXPECTED_SOURCE_KINDS)}")

    freshness = _set(metadata.get("freshness_scopes"))
    if freshness != EXPECTED_FRESHNESS:
        fail(errors, f"freshness scope set mismatch missing={sorted(EXPECTED_FRESHNESS-freshness)} extra={sorted(freshness-EXPECTED_FRESHNESS)}")

    sensitivity = _set(metadata.get("sensitivity_values"))
    if sensitivity != EXPECTED_SENSITIVITY:
        fail(errors, f"sensitivity set mismatch missing={sorted(EXPECTED_SENSITIVITY-sensitivity)} extra={sorted(sensitivity-EXPECTED_SENSITIVITY)}")

    role_ids = _set(metadata.get("canonical_role_ids"))
    if role_ids != EXPECTED_ROLE_IDS:
        fail(errors, f"canonical role set mismatch missing={sorted(EXPECTED_ROLE_IDS-role_ids)} extra={sorted(role_ids-EXPECTED_ROLE_IDS)}")

    aliases = metadata.get("role_aliases")
    if not isinstance(aliases, dict) or not aliases:
        fail(errors, "role_aliases must be a non-empty object")
    elif any(not isinstance(alias, str) or not isinstance(role, str) or role not in role_ids for alias, role in aliases.items()):
        fail(errors, "every role_aliases value must be a canonical role ID")

    freshness_bindings = metadata.get("freshness_binding_fields")
    if freshness_bindings != EXPECTED_FRESHNESS_BINDINGS:
        fail(errors, "freshness_binding_fields must match the canonical freshness-to-binding map")

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

    expected_profile_keys = {
        "default_evidence_class",
        "default_sensitivity",
        "default_solver_visible",
        "repository_backed",
        "task_scoped",
        "chunk_strategy",
        "required_bindings",
        "required_freshness",
    }
    chunk_types = _set(metadata.get("chunk_types"))
    for source_kind, profile in profiles.items():
        if not isinstance(profile, dict):
            fail(errors, f"{source_kind}: source profile must be an object")
            continue
        if set(profile) != expected_profile_keys:
            fail(errors, f"{source_kind}: source profile keys must be {sorted(expected_profile_keys)}")
        if profile.get("default_evidence_class") not in visibility_classes:
            fail(errors, f"{source_kind}: unknown evidence class {profile.get('default_evidence_class')!r}")
        if profile.get("default_sensitivity") not in EXPECTED_SENSITIVITY:
            fail(errors, f"{source_kind}: invalid sensitivity {profile.get('default_sensitivity')!r}")
        if not isinstance(profile.get("default_solver_visible"), bool):
            fail(errors, f"{source_kind}: default_solver_visible must be boolean")
        if not isinstance(profile.get("repository_backed"), bool) or not isinstance(profile.get("task_scoped"), bool):
            fail(errors, f"{source_kind}: repository_backed/task_scoped must be boolean")
        if profile.get("chunk_strategy") not in chunk_types:
            fail(errors, f"{source_kind}: unknown chunk strategy {profile.get('chunk_strategy')!r}")
        required_bindings = _set(profile.get("required_bindings"))
        if profile.get("repository_backed") is True and not {"source_path", "git_blob_sha"} <= required_bindings:
            fail(errors, f"{source_kind}: repository-backed profile must require source_path and git_blob_sha")
        if profile.get("task_scoped") is True and not {"task_id", "task_commit"} <= required_bindings:
            fail(errors, f"{source_kind}: task-scoped profile must require task_id and task_commit")
        required_freshness = _set(profile.get("required_freshness"))
        if not required_freshness or not required_freshness <= EXPECTED_FRESHNESS:
            fail(errors, f"{source_kind}: required_freshness is empty or invalid")
        for scope in required_freshness:
            field = EXPECTED_FRESHNESS_BINDINGS.get(scope)
            if field and field not in required_bindings:
                fail(errors, f"{source_kind}: freshness {scope} requires required binding {field}")

    required_fields = _set(metadata.get("required_chunk_fields"))
    for field in {
        "document_id", "chunk_id", "source_uri", "source_kind", "source_version",
        "content_hash", "evidence_class", "sensitivity", "solver_visible",
        "stage_applicability", "role_applicability", "freshness_scope", "chunk_type",
        "structural_locator", "ordinal",
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
            source_enum = _set(properties.get("source_kind", {}).get("enum", []) if isinstance(properties.get("source_kind"), dict) else [])
            if source_enum != source_kinds:
                fail(errors, "retrieval chunk source_kind enum must match registry")
            evidence_enum = _set(properties.get("evidence_class", {}).get("enum", []) if isinstance(properties.get("evidence_class"), dict) else [])
            if evidence_enum != visibility_classes:
                fail(errors, "retrieval chunk evidence_class enum must match evidence visibility registry")
            freshness_enum = _set(properties.get("freshness_scope", {}).get("items", {}).get("enum", []) if isinstance(properties.get("freshness_scope"), dict) else [])
            if freshness_enum != freshness:
                fail(errors, "retrieval chunk freshness_scope enum must match metadata registry")
            stage_enum = _set(properties.get("stage_applicability", {}).get("items", {}).get("enum", []) if isinstance(properties.get("stage_applicability"), dict) else [])
            if stage_enum != stage_ids | {"ALL_AUTHORIZED_STAGES"}:
                fail(errors, "retrieval chunk stage_applicability enum must match registered stage IDs")
            role_enum = _set(properties.get("role_applicability", {}).get("items", {}).get("enum", []) if isinstance(properties.get("role_applicability"), dict) else [])
            if role_enum != role_ids | {"ALL_AUTHORIZED_ROLES"}:
                fail(errors, "retrieval chunk role_applicability enum must match canonical role IDs")
        if not isinstance(chunk_schema.get("allOf"), list) or len(chunk_schema.get("allOf", [])) < len(EXPECTED_SOURCE_KINDS):
            fail(errors, "retrieval chunk schema must contain fail-closed conditional source-profile constraints")

    if isinstance(manifest_schema, dict):
        if manifest_schema.get("$id") != "terminus-retrieval-manifest-v1":
            fail(errors, "retrieval manifest schema must declare $id terminus-retrieval-manifest-v1")
        properties = manifest_schema.get("properties", {})
        if isinstance(properties, dict):
            visibility_const = properties.get("evidence_visibility_version", {}).get("const") if isinstance(properties.get("evidence_visibility_version"), dict) else None
            if visibility_const != "1.1":
                fail(errors, "retrieval manifest must bind evidence visibility version 1.1")
            source_names = _set(properties.get("source_kind_counts", {}).get("propertyNames", {}).get("enum", []) if isinstance(properties.get("source_kind_counts"), dict) else [])
            if source_names != source_kinds:
                fail(errors, "retrieval manifest source_kind_counts names must match registry")
            evidence_names = _set(properties.get("evidence_class_counts", {}).get("propertyNames", {}).get("enum", []) if isinstance(properties.get("evidence_class_counts"), dict) else [])
            if evidence_names != visibility_classes:
                fail(errors, "retrieval manifest evidence_class_counts names must match visibility registry")
            role_names = _set(properties.get("role_contract_hashes", {}).get("propertyNames", {}).get("enum", []) if isinstance(properties.get("role_contract_hashes"), dict) else [])
            if role_names != role_ids:
                fail(errors, "retrieval manifest role_contract_hashes names must match canonical role IDs")

    if not isinstance(requirement_schema, dict) or requirement_schema.get("$id") != "terminus-solver-visible-requirement-contract-v1":
        fail(errors, "solver-visible requirement projection schema is missing or has wrong $id")

    global_tokens = metadata.get("global_applicability_tokens", {})
    if not isinstance(global_tokens, dict) or global_tokens.get("stage") != "ALL_AUTHORIZED_STAGES" or global_tokens.get("role") != "ALL_AUTHORIZED_ROLES":
        fail(errors, "global applicability tokens are missing or invalid")

    expected_profile_classes = {
        "TASK_INSTRUCTION": "SOLVER_VISIBLE_TASK",
        "TASK_DOCUMENTATION": "SOLVER_VISIBLE_TASK",
        "TASK_CODE": "SOLVER_VISIBLE_TASK",
        "SOLVER_VISIBLE_REQUIREMENT_CONTRACT": "SOLVER_VISIBLE_TASK",
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

    # Semantic guardrail self-tests ensure the validator itself rejects representative fail-open cases.
    sample_common: dict[str, object] = {
        "metadata_contract_version": "1.0",
        "document_id": "document-1234",
        "chunk_id": "chunk-1234",
        "source_uri": "repo://task/instruction.md",
        "source_version": "abc",
        "content_hash": "sha256:" + "0" * 64,
        "stage_applicability": ["INSTRUCTION_DRAFT"],
        "role_applicability": ["A7_INSTRUCTION_WRITER"],
        "chunk_type": "DOCUMENT",
        "structural_locator": "document",
        "ordinal": 0,
    }
    valid_task = {
        **sample_common,
        "source_kind": "TASK_INSTRUCTION",
        "source_path": "task/instruction.md",
        "git_blob_sha": "a" * 40,
        "task_id": "task",
        "task_commit": "b" * 40,
        "evidence_class": "SOLVER_VISIBLE_TASK",
        "sensitivity": "SOLVER_VISIBLE",
        "solver_visible": True,
        "freshness_scope": ["GIT_BLOB_SHA", "TASK_COMMIT"],
    }
    if validate_chunk_semantics(valid_task, metadata, stage_ids, role_ids):
        fail(errors, "retrieval semantic guardrail rejected a valid task-instruction sample")

    bad_oracle = {
        **valid_task,
        "source_kind": "SOLUTION_ORACLE",
        "evidence_class": "SOLVER_VISIBLE_TASK",
        "sensitivity": "SOLVER_VISIBLE",
        "solver_visible": True,
    }
    if not validate_chunk_semantics(bad_oracle, metadata, stage_ids, role_ids):
        fail(errors, "retrieval semantic guardrail failed to reject solver-visible Oracle metadata")

    missing_commit = dict(valid_task)
    missing_commit.pop("task_commit", None)
    if not validate_chunk_semantics(missing_commit, metadata, stage_ids, role_ids):
        fail(errors, "retrieval semantic guardrail failed to reject missing task_commit")

    bad_stage = dict(valid_task)
    bad_stage["stage_applicability"] = ["INSTRUCTON_DRAFT"]
    if not validate_chunk_semantics(bad_stage, metadata, stage_ids, role_ids):
        fail(errors, "retrieval semantic guardrail failed to reject unknown stage ID")

    bad_role = dict(valid_task)
    bad_role["role_applicability"] = ["Q4_SPEC_REVIEWER"]
    if not validate_chunk_semantics(bad_role, metadata, stage_ids, role_ids):
        fail(errors, "retrieval semantic guardrail failed to reject unknown role ID")

    if errors:
        print("Terminus retrieval metadata validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Terminus retrieval metadata validation PASS")
    print(
        f"metadata_contract=1.0 visibility={visibility_version} "
        f"source_kinds={len(source_kinds)} evidence_classes={len(visibility_classes)} "
        f"registered_stages={len(stage_ids)} canonical_roles={len(role_ids)} "
        f"freshness_scopes={len(freshness)} fail_closed=enabled"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
