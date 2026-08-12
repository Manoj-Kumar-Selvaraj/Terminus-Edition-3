#!/usr/bin/env python3
"""Validate the machine-readable Terminus lifecycle stage contract registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
REGISTRY_PATH = T / "agents" / "stage_contracts.json"
SCHEMA_PATH = T / "agents" / "schemas" / "stage_contracts.schema.json"

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

NON_STAGE_TRANSITIONS = {"FROZEN_CANDIDATE", "END"}


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
        if not (ref.startswith(".terminus/") or ref.startswith("TERMINUS_3_AI_INSTRUCTIONS.md")):
            continue
        path = ROOT / ref
        if not path.exists():
            fail(errors, f"{stage_id}: {field} references missing repository file {ref}")


def main() -> int:
    errors: list[str] = []
    registry = load_json(REGISTRY_PATH, errors)
    schema = load_json(SCHEMA_PATH, errors)

    if isinstance(schema, dict):
        if schema.get("$id") != "terminus-stage-contracts-v1":
            fail(errors, "stage-contract schema must declare $id terminus-stage-contracts-v1")
        if schema.get("additionalProperties") is not False:
            fail(errors, "stage-contract schema must reject undeclared top-level fields")

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
                ensure_string_list(errors, stage_id, f"input_contract.{field}", input_contract.get(field))

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
                ensure_string_list(errors, stage_id, f"output_contract.{field}", output_contract.get(field))
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
            fail(errors, f"{stage_id}: failure_routes must map non-empty strings to non-empty strings")

        transition = stage.get("success_transition")
        if not isinstance(transition, str) or not transition:
            fail(errors, f"{stage_id}: success_transition must be a non-empty string")

    if len(ids) != len(set(ids)):
        fail(errors, "stage contract registry contains duplicate stage ids")

    id_set = set(ids)
    missing_required_stages = REQUIRED_STAGE_IDS - id_set
    if missing_required_stages:
        fail(errors, f"stage contract registry missing required stages: {sorted(missing_required_stages)}")

    for stage in stages:
        if not isinstance(stage, dict):
            continue
        transition = stage.get("success_transition")
        if isinstance(transition, str) and transition not in id_set | NON_STAGE_TRANSITIONS:
            fail(errors, f"{stage.get('id', '<unknown>')}: success_transition references unknown stage/state {transition!r}")

    if errors:
        print("Terminus stage-contract validation FAILED:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("Terminus stage-contract validation PASS")
    print(f"contract_version=1.0 stages={len(stages)} required_stages={len(REQUIRED_STAGE_IDS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
