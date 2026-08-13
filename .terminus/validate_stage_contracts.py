#!/usr/bin/env python3
"""Validate Terminus lifecycle stage contracts and evidence visibility boundaries."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
REGISTRY_PATH = T / "agents" / "stage_contracts.json"
SCHEMA_PATH = T / "agents" / "schemas" / "stage_contracts.schema.json"
VISIBILITY_PATH = T / "agents" / "evidence_visibility.json"
VISIBILITY_SCHEMA_PATH = T / "agents" / "schemas" / "evidence_visibility.schema.json"
STAGE_POLICY_PATH = T / "agents" / "STAGE_CONTRACTS.md"
VISIBILITY_POLICY_PATH = T / "agents" / "EVIDENCE_VISIBILITY.md"
INSTRUCTION_POLICY_PATH = T / "agents" / "INSTRUCTION_POLICY.md"
AGENT_SYSTEM_PATH = T / "AGENT_SYSTEM.md"

REQUIRED_STAGE_IDS = {
    "RULE_RESOLUTION",
    "WORK_PACKAGE_RESEARCH",
    "SYSTEM_ARCHITECTURE",
    "DEFECT_TOPOLOGY",
    "ENVIRONMENT_BUILD",
    "REFERENCE_SOLUTION",
    "VERIFIER_BUILD",
    "HUMAN_WRITING_RESEARCH",
    "INSTRUCTION_DRAFT",
    "SPEC_ALIGNMENT",
    "DOCUMENTATION_DRAFT",
    "FORMAT_GATE",
    "ASSEMBLY",
    "COMPLEXITY_GATE",
    "RUNTIME_AUTHENTICITY",
    "DETERMINISTIC_VALIDATION",
    "QUALITY_INTERLOCK",
    "PRE_LLMAJ",
    "MODEL_DIAGNOSTIC",
    "OFFICIAL_MODEL_TRIALS",
    "TRIAL_ANALYSIS",
    "FINAL_REVIEW",
    "SUBMISSION_READY",
}

REQUIRED_STAGE_KEYS = {
    "id",
    "lifecycle",
    "owner",
    "role_class",
    "policy_files",
    "prompt_files",
    "input_contract",
    "output_contract",
    "evidence_required",
    "deterministic_validators",
    "semantic_reviewers",
    "failure_routes",
    "success_transition",
    "stale_on",
}

REQUIRED_INPUT_KEYS = {"required_fields", "optional_fields"}
REQUIRED_OUTPUT_KEYS = {
    "status_values",
    "required_fields",
    "optional_fields",
    "persisted_artifacts",
}

REQUIRED_VISIBILITY_KEYS = {
    "stage_id",
    "required_evidence_classes",
    "allowed_optional_evidence_classes",
    "excluded_evidence_classes",
    "retrieval_mode",
    "output_disposition",
}

VALID_LIFECYCLES = {"creation", "review", "evaluation", "submission"}
VALID_ROLE_CLASSES = {
    "CONTROLLER",
    "PRODUCER",
    "FIXER",
    "REVIEWER",
    "ADJUDICATOR",
    "SIMULATOR",
    "EXTERNAL_GATE",
}
VALID_RETRIEVAL_MODES = {
    "EXACT_ONLY",
    "FILTERED_HYBRID",
    "SOLVER_VISIBLE_ONLY",
    "EXTERNAL_BOUND",
}
VALID_OUTPUT_DISPOSITIONS = {
    "EPHEMERAL",
    "DURABLE_CONTROL_PLANE",
    "PRIVATE_CONTROL_PLANE",
    "TASK_ARTIFACT",
    "REVIEW_EVIDENCE",
    "EXTERNAL_EVIDENCE",
}

NON_STAGE_TRANSITIONS = {"FROZEN_CANDIDATE", "END"}

AGENT_SYSTEM_BINDING_MARKERS = [
    "Structured execution bindings",
    ".terminus/agents/stage_contracts.json",
    ".terminus/agents/STAGE_CONTRACTS.md",
    ".terminus/agents/schemas/stage_contracts.schema.json",
    ".terminus/agents/INSTRUCTION_POLICY.md",
    "INPUT CONTRACT",
    "OUTPUT CONTRACT",
    "DETERMINISTIC VALIDATORS",
    "SEMANTIC REVIEWERS",
    "FAILURE ROUTES",
    "SUCCESS TRANSITION",
    "STALE_ON",
]

STAGE_POLICY_MARKERS = [
    "Stage-contract policy version: `1.0`",
    "Canonical stage fields",
    "Validator honesty rule",
    "Input/output contract rule",
    "Runtime prompt projection",
    "Section-to-stage bindings",
    "Failure routing principle",
    "Staleness principle",
]

VISIBILITY_POLICY_MARKERS = [
    "Evidence visibility policy version: `1.1`",
    "required_evidence_classes",
    "allowed_optional_evidence_classes",
    "excluded_evidence_classes",
    "There is no implicit/unclassified retrieval bucket",
    "Retrieval modes",
    "SOLVER_VISIBLE_ONLY",
    "Output disposition",
    "Future RAG requirement",
    "filter by visibility **before** semantic ranking",
]

INSTRUCTION_POLICY_MARKERS = [
    "Instruction policy version: `1.0`",
    "<=2 short paragraphs or <=20 concise bullets",
    "Required instruction content",
    "Instruction versus solver-visible documentation",
    "Implementation-diagnosis boundary",
    "Current-state claims and evidence",
    "Jira/Slack handoff test",
    "Requirement-completeness test",
    "Reverse-outline test",
    "Spec-file-loophole test",
    "Current-state evidence test",
    "Structured processing contract",
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


def load_text(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        fail(errors, f"missing required file: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def ensure_string_list(errors: list[str], stage_id: str, field: str, value: object) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        fail(errors, f"{stage_id}: {field} must be a list of strings")
        return
    if len(value) != len(set(value)):
        fail(errors, f"{stage_id}: {field} contains duplicates")


def validate_file_references(errors: list[str], stage_id: str, field: str, refs: object) -> None:
    if not isinstance(refs, list):
        return
    for ref in refs:
        if not isinstance(ref, str):
            continue
        if not (
            ref.startswith(".terminus/")
            or ref.startswith("TERMINUS_3_AI_INSTRUCTIONS.md")
        ):
            continue
        path = ROOT / ref
        if not path.exists():
            fail(errors, f"{stage_id}: {field} references missing repository file {ref}")


def require_markers(errors: list[str], text: str, path: Path, markers: list[str]) -> None:
    for marker in markers:
        if marker.lower() not in text.lower():
            fail(errors, f"{path.relative_to(ROOT)} missing required marker: {marker}")


def validate_visibility(
    errors: list[str], visibility: object, stage_ids: set[str]
) -> tuple[int, set[str]]:
    if not isinstance(visibility, dict):
        fail(errors, "evidence visibility registry must be a JSON object")
        return 0, set()

    if visibility.get("visibility_version") != "1.1":
        fail(errors, "evidence visibility registry must declare visibility_version 1.1")

    classes_raw = visibility.get("evidence_classes", {})
    if not isinstance(classes_raw, dict) or not classes_raw:
        fail(errors, "evidence visibility registry must define evidence_classes")
        evidence_classes: set[str] = set()
    else:
        evidence_classes = set(classes_raw)
        for class_id, definition in classes_raw.items():
            if not isinstance(class_id, str) or not class_id:
                fail(errors, "evidence class IDs must be non-empty strings")
                continue
            if not isinstance(definition, dict):
                fail(errors, f"evidence class {class_id}: definition must be an object")
                continue
            if not isinstance(definition.get("description"), str) or not definition.get(
                "description"
            ):
                fail(errors, f"evidence class {class_id}: missing description")
            if definition.get("default_sensitivity") not in {
                "PUBLIC",
                "SOLVER_VISIBLE",
                "CONTROL_PLANE",
                "PRIVATE",
                "RESTRICTED",
            }:
                fail(errors, f"evidence class {class_id}: invalid default_sensitivity")

    entries = visibility.get("stages", [])
    if not isinstance(entries, list):
        fail(errors, "evidence visibility registry 'stages' must be a list")
        return 0, evidence_classes

    visibility_ids: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            fail(errors, f"visibility stage[{index}] must be an object")
            continue

        stage_id = entry.get("stage_id")
        if not isinstance(stage_id, str) or not stage_id:
            fail(errors, f"visibility stage[{index}] missing stage_id")
            stage_id = f"<visibility-{index}>"
        else:
            visibility_ids.append(stage_id)

        missing = REQUIRED_VISIBILITY_KEYS - set(entry)
        extra = set(entry) - REQUIRED_VISIBILITY_KEYS
        if missing:
            fail(errors, f"{stage_id}: missing visibility keys: {sorted(missing)}")
        if extra:
            fail(errors, f"{stage_id}: undeclared visibility keys: {sorted(extra)}")

        required = entry.get("required_evidence_classes")
        optional = entry.get("allowed_optional_evidence_classes")
        excluded = entry.get("excluded_evidence_classes")
        for field, value in [
            ("required_evidence_classes", required),
            ("allowed_optional_evidence_classes", optional),
            ("excluded_evidence_classes", excluded),
            ("output_disposition", entry.get("output_disposition")),
        ]:
            ensure_string_list(errors, stage_id, field, value)

        if all(isinstance(value, list) for value in (required, optional, excluded)):
            required_set = set(required)
            optional_set = set(optional)
            excluded_set = set(excluded)
            if required_set & optional_set:
                fail(errors, f"{stage_id}: required and optional evidence classes overlap")
            if required_set & excluded_set:
                fail(errors, f"{stage_id}: required and excluded evidence classes overlap")
            if optional_set & excluded_set:
                fail(errors, f"{stage_id}: optional and excluded evidence classes overlap")
            classified = required_set | optional_set | excluded_set
            unknown = classified - evidence_classes
            if unknown:
                fail(errors, f"{stage_id}: unknown evidence classes: {sorted(unknown)}")
            missing_classes = evidence_classes - classified
            if missing_classes:
                fail(
                    errors,
                    f"{stage_id}: unclassified evidence classes: {sorted(missing_classes)}",
                )

        mode = entry.get("retrieval_mode")
        if mode not in VALID_RETRIEVAL_MODES:
            fail(errors, f"{stage_id}: invalid retrieval_mode {mode!r}")

        dispositions = entry.get("output_disposition")
        if isinstance(dispositions, list):
            unknown_dispositions = set(dispositions) - VALID_OUTPUT_DISPOSITIONS
            if unknown_dispositions:
                fail(
                    errors,
                    f"{stage_id}: invalid output dispositions: {sorted(unknown_dispositions)}",
                )
            if not dispositions:
                fail(errors, f"{stage_id}: output_disposition cannot be empty")

    if len(visibility_ids) != len(set(visibility_ids)):
        fail(errors, "evidence visibility registry contains duplicate stage ids")

    visibility_id_set = set(visibility_ids)
    if visibility_id_set != stage_ids:
        missing = stage_ids - visibility_id_set
        extra = visibility_id_set - stage_ids
        if missing:
            fail(errors, f"evidence visibility missing stage ids: {sorted(missing)}")
        if extra:
            fail(errors, f"evidence visibility has unknown stage ids: {sorted(extra)}")

    entries_by_id = {
        entry.get("stage_id"): entry for entry in entries if isinstance(entry, dict)
    }
    critical_exclusions = {
        "INSTRUCTION_DRAFT": {
            "PRIVATE_CREATION_DESIGN",
            "SOLUTION_ORACLE",
            "VERIFIER_PRIVATE",
            "PRIOR_REVIEW_RESULTS",
        },
        "VERIFIER_BUILD": {"SOLUTION_ORACLE", "PRIOR_REVIEW_RESULTS"},
        "MODEL_DIAGNOSTIC": {
            "PRIVATE_CREATION_DESIGN",
            "SOLUTION_ORACLE",
            "VERIFIER_PRIVATE",
            "PRIOR_REVIEW_RESULTS",
            "MODEL_TRIAL_EVIDENCE",
        },
        "OFFICIAL_MODEL_TRIALS": {
            "PRIVATE_CREATION_DESIGN",
            "SOLUTION_ORACLE",
            "VERIFIER_PRIVATE",
            "PRIOR_REVIEW_RESULTS",
        },
    }
    for stage_id, expected_excluded in critical_exclusions.items():
        entry = entries_by_id.get(stage_id, {})
        excluded = set(entry.get("excluded_evidence_classes", []))
        missing = expected_excluded - excluded
        if missing:
            fail(
                errors,
                f"{stage_id}: missing critical isolation exclusions: {sorted(missing)}",
            )

    model_diag = entries_by_id.get("MODEL_DIAGNOSTIC", {})
    if model_diag.get("retrieval_mode") != "SOLVER_VISIBLE_ONLY":
        fail(errors, "MODEL_DIAGNOSTIC must use SOLVER_VISIBLE_ONLY retrieval mode")

    return len(entries), evidence_classes


def main() -> int:
    errors: list[str] = []
    registry = load_json(REGISTRY_PATH, errors)
    schema = load_json(SCHEMA_PATH, errors)
    visibility = load_json(VISIBILITY_PATH, errors)
    visibility_schema = load_json(VISIBILITY_SCHEMA_PATH, errors)
    stage_policy = load_text(STAGE_POLICY_PATH, errors)
    visibility_policy = load_text(VISIBILITY_POLICY_PATH, errors)
    instruction_policy = load_text(INSTRUCTION_POLICY_PATH, errors)
    agent_system = load_text(AGENT_SYSTEM_PATH, errors)

    require_markers(errors, stage_policy, STAGE_POLICY_PATH, STAGE_POLICY_MARKERS)
    require_markers(
        errors,
        visibility_policy,
        VISIBILITY_POLICY_PATH,
        VISIBILITY_POLICY_MARKERS,
    )
    require_markers(
        errors,
        instruction_policy,
        INSTRUCTION_POLICY_PATH,
        INSTRUCTION_POLICY_MARKERS,
    )
    require_markers(errors, agent_system, AGENT_SYSTEM_PATH, AGENT_SYSTEM_BINDING_MARKERS)

    if not re.search(r"Agent-system policy version: `[^`]+`", agent_system):
        fail(errors, "AGENT_SYSTEM.md must declare an Agent-system policy version")

    if isinstance(schema, dict):
        if schema.get("$id") != "terminus-stage-contracts-v1":
            fail(errors, "stage-contract schema must declare $id terminus-stage-contracts-v1")
        if schema.get("additionalProperties") is not False:
            fail(errors, "stage-contract schema must reject undeclared top-level fields")

    if isinstance(visibility_schema, dict):
        if visibility_schema.get("$id") != "terminus-evidence-visibility-v1":
            fail(
                errors,
                "evidence-visibility schema must declare $id terminus-evidence-visibility-v1",
            )
        if visibility_schema.get("additionalProperties") is not False:
            fail(
                errors,
                "evidence-visibility schema must reject undeclared top-level fields",
            )

    if not isinstance(registry, dict):
        fail(errors, "stage contract registry must be a JSON object")
        registry = {}

    if registry.get("contract_version") != "1.0":
        fail(errors, "stage contract registry must declare contract_version 1.0")

    stages = registry.get("stages", [])
    if not isinstance(stages, list):
        fail(errors, "stage contract registry 'stages' must be a list")
        stages = []

    ids: list[str] = []
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            fail(errors, f"stage[{index}] must be an object")
            continue

        stage_id = stage.get("id")
        if not isinstance(stage_id, str) or not stage_id:
            fail(errors, f"stage[{index}] missing string id")
            stage_id = f"<stage-{index}>"
        else:
            ids.append(stage_id)

        missing = REQUIRED_STAGE_KEYS - set(stage)
        extra = set(stage) - REQUIRED_STAGE_KEYS
        if missing:
            fail(errors, f"{stage_id}: missing stage keys: {sorted(missing)}")
        if extra:
            fail(errors, f"{stage_id}: undeclared stage keys: {sorted(extra)}")

        lifecycle = stage.get("lifecycle")
        if lifecycle not in VALID_LIFECYCLES:
            fail(errors, f"{stage_id}: invalid lifecycle {lifecycle!r}")
        role_class = stage.get("role_class")
        if role_class not in VALID_ROLE_CLASSES:
            fail(errors, f"{stage_id}: invalid role_class {role_class!r}")
        owner = stage.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            fail(errors, f"{stage_id}: owner must be a non-empty string")

        for field in [
            "policy_files",
            "prompt_files",
            "evidence_required",
            "deterministic_validators",
            "semantic_reviewers",
            "stale_on",
        ]:
            ensure_string_list(errors, stage_id, field, stage.get(field))

        validate_file_references(errors, stage_id, "policy_files", stage.get("policy_files"))
        validate_file_references(errors, stage_id, "prompt_files", stage.get("prompt_files"))

        input_contract = stage.get("input_contract")
        if not isinstance(input_contract, dict):
            fail(errors, f"{stage_id}: input_contract must be an object")
        else:
            missing_input = REQUIRED_INPUT_KEYS - set(input_contract)
            extra_input = set(input_contract) - REQUIRED_INPUT_KEYS
            if missing_input:
                fail(errors, f"{stage_id}: input_contract missing keys: {sorted(missing_input)}")
            if extra_input:
                fail(errors, f"{stage_id}: input_contract undeclared keys: {sorted(extra_input)}")
            for field in REQUIRED_INPUT_KEYS:
                ensure_string_list(
                    errors, stage_id, f"input_contract.{field}", input_contract.get(field)
                )

        output_contract = stage.get("output_contract")
        if not isinstance(output_contract, dict):
            fail(errors, f"{stage_id}: output_contract must be an object")
        else:
            missing_output = REQUIRED_OUTPUT_KEYS - set(output_contract)
            extra_output = set(output_contract) - REQUIRED_OUTPUT_KEYS
            if missing_output:
                fail(errors, f"{stage_id}: output_contract missing keys: {sorted(missing_output)}")
            if extra_output:
                fail(errors, f"{stage_id}: output_contract undeclared keys: {sorted(extra_output)}")
            for field in REQUIRED_OUTPUT_KEYS:
                ensure_string_list(
                    errors,
                    stage_id,
                    f"output_contract.{field}",
                    output_contract.get(field),
                )
            statuses = output_contract.get("status_values")
            if isinstance(statuses, list) and not statuses:
                fail(errors, f"{stage_id}: output_contract.status_values cannot be empty")
            required_fields = output_contract.get("required_fields")
            if isinstance(required_fields, list) and not required_fields:
                fail(errors, f"{stage_id}: output_contract.required_fields cannot be empty")

        failure_routes = stage.get("failure_routes")
        if not isinstance(failure_routes, dict):
            fail(errors, f"{stage_id}: failure_routes must be an object")
        elif any(
            not isinstance(key, str)
            or not key
            or not isinstance(value, str)
            or not value.strip()
            for key, value in failure_routes.items()
        ):
            fail(
                errors,
                f"{stage_id}: failure_routes must map non-empty strings to non-empty strings",
            )

        transition = stage.get("success_transition")
        if not isinstance(transition, str) or not transition:
            fail(errors, f"{stage_id}: success_transition must be a non-empty string")

    if len(ids) != len(set(ids)):
        fail(errors, "stage contract registry contains duplicate stage ids")

    id_set = set(ids)
    missing_required_stages = REQUIRED_STAGE_IDS - id_set
    if missing_required_stages:
        fail(
            errors,
            f"stage contract registry missing required stages: {sorted(missing_required_stages)}",
        )

    for stage in stages:
        if not isinstance(stage, dict):
            continue
        transition = stage.get("success_transition")
        if isinstance(transition, str) and transition not in id_set | NON_STAGE_TRANSITIONS:
            fail(
                errors,
                f"{stage.get('id', '<unknown>')}: success_transition references unknown stage/state {transition!r}",
            )

    instruction_stage = next(
        (
            stage
            for stage in stages
            if isinstance(stage, dict) and stage.get("id") == "INSTRUCTION_DRAFT"
        ),
        None,
    )
    if isinstance(instruction_stage, dict):
        policy_files = instruction_stage.get("policy_files", [])
        if ".terminus/agents/INSTRUCTION_POLICY.md" not in policy_files:
            fail(errors, "INSTRUCTION_DRAFT must bind .terminus/agents/INSTRUCTION_POLICY.md")
        required_inputs = instruction_stage.get("input_contract", {}).get(
            "required_fields", []
        )
        for field in [
            "ENGINEERING_OBJECTIVE",
            "REQUIRED_END_STATE",
            "FUNCTIONAL_REQUIREMENTS",
            "REFERENCED_DOCS",
            "REQUIRED_OUTPUTS",
        ]:
            if field not in required_inputs:
                fail(errors, f"INSTRUCTION_DRAFT missing required input contract field {field}")

    visibility_count, evidence_classes = validate_visibility(errors, visibility, id_set)

    if errors:
        print("Terminus stage-contract validation FAILED:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("Terminus stage-contract validation PASS")
    print(
        f"contract_version=1.0 visibility_version=1.1 stages={len(stages)} "
        f"visibility_stages={visibility_count} evidence_classes={len(evidence_classes)} "
        f"required_stages={len(REQUIRED_STAGE_IDS)} instruction_policy=1.0 "
        "structured_bindings=present retrieval_boundaries=classified"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
