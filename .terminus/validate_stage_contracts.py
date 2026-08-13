#!/usr/bin/env python3
"""Validate Terminus lifecycle, visibility, and completion stage contracts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
AGENTS = T / "agents"
REGISTRY_PATH = AGENTS / "stage_contracts.json"
SCHEMA_PATH = AGENTS / "schemas" / "stage_contracts.schema.json"
VISIBILITY_PATH = AGENTS / "evidence_visibility.json"
VISIBILITY_SCHEMA_PATH = AGENTS / "schemas" / "evidence_visibility.schema.json"
VISIBILITY_POLICY_PATH = AGENTS / "EVIDENCE_VISIBILITY.md"
COMPLETION_PATH = AGENTS / "stage_contract_completion.json"
COMPLETION_SCHEMA_PATH = AGENTS / "schemas" / "stage_contract_completion.schema.json"
COMPLETION_POLICY_PATH = AGENTS / "STAGE_CONTRACT_COMPLETION.md"
STAGE_POLICY_PATH = AGENTS / "STAGE_CONTRACTS.md"
INSTRUCTION_POLICY_PATH = AGENTS / "INSTRUCTION_POLICY.md"
CREATION_PIPELINE_PATH = AGENTS / "CREATION_PIPELINE.md"
CREATOR_REGISTRY_PATH = AGENTS / "CREATOR_AGENT_REGISTRY.md"
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

EVIDENCE_CLASSES = {
    "CONTROL_PLANE_POLICY",
    "SOLVER_VISIBLE_TASK",
    "PRIVATE_CREATION_DESIGN",
    "SOLUTION_ORACLE",
    "VERIFIER_PRIVATE",
    "CURRENT_REVIEW_PACKETS",
    "PRIOR_REVIEW_RESULTS",
    "CI_RUNTIME_EVIDENCE",
    "DURABLE_SESSION_STATE",
    "PUBLIC_REFERENCES",
    "MODEL_TRIAL_EVIDENCE",
    "FINAL_PACKAGE_EVIDENCE",
}
VALID_RETRIEVAL_MODES = {"EXACT_ONLY", "FILTERED_HYBRID", "SOLVER_VISIBLE_ONLY", "EXTERNAL_BOUND"}
VALID_OUTPUT_DISPOSITIONS = {
    "EPHEMERAL",
    "DURABLE_CONTROL_PLANE",
    "PRIVATE_CONTROL_PLANE",
    "TASK_ARTIFACT",
    "REVIEW_EVIDENCE",
    "EXTERNAL_EVIDENCE",
}

EXPECTED_CREATION_CHAIN = [
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
    "FROZEN_CANDIDATE",
    "QUALITY_INTERLOCK",
]

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

VISIBILITY_POLICY_MARKERS = [
    "Evidence visibility policy version: `1.1`",
    "required evidence",
    "allowed optional evidence",
    "excluded evidence",
    "retrieval",
    "RAG",
]

COMPLETION_POLICY_MARKERS = [
    "Completion policy version: `1.2`",
    "A2 two-phase contract",
    "SYSTEM_ARCHITECTURE",
    "ENVIRONMENT_BUILD",
    "Freeze-state contract",
    "FROZEN_CANDIDATE",
    "Canonical creation chain",
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
        if not (ref.startswith(".terminus/") or ref.startswith("TERMINUS_3_AI_INSTRUCTIONS.md")):
            continue
        path = ROOT / ref
        if not path.exists():
            fail(errors, f"{stage_id}: {field} references missing repository file {ref}")


def require_markers(errors: list[str], text: str, path: Path, markers: list[str]) -> None:
    for marker in markers:
        if marker.lower() not in text.lower():
            fail(errors, f"{path.relative_to(ROOT)} missing required marker: {marker}")


def validate_visibility(errors: list[str], stage_ids: set[str]) -> tuple[str, int, int]:
    visibility = load_json(VISIBILITY_PATH, errors)
    schema = load_json(VISIBILITY_SCHEMA_PATH, errors)
    policy = load_text(VISIBILITY_POLICY_PATH, errors)
    require_markers(errors, policy, VISIBILITY_POLICY_PATH, VISIBILITY_POLICY_MARKERS)

    if isinstance(schema, dict):
        if schema.get("$id") != "terminus-evidence-visibility-v1.1":
            fail(errors, "evidence-visibility schema must declare $id terminus-evidence-visibility-v1.1")
        if schema.get("additionalProperties") is not False:
            fail(errors, "evidence-visibility schema must reject undeclared top-level fields")

    if not isinstance(visibility, dict):
        fail(errors, "evidence visibility registry must be a JSON object")
        return "?", 0, 0

    version = visibility.get("visibility_version")
    if version != "1.1":
        fail(errors, "evidence visibility registry must declare visibility_version 1.1")

    declared_classes = visibility.get("evidence_classes", {})
    if not isinstance(declared_classes, dict):
        fail(errors, "evidence_visibility.evidence_classes must be an object")
        declared_classes = {}
    if set(declared_classes) != EVIDENCE_CLASSES:
        fail(
            errors,
            "evidence visibility classes must exactly match canonical set; "
            f"missing={sorted(EVIDENCE_CLASSES - set(declared_classes))} "
            f"extra={sorted(set(declared_classes) - EVIDENCE_CLASSES)}",
        )

    stage_visibility = visibility.get("stages", {})
    if not isinstance(stage_visibility, dict):
        fail(errors, "evidence_visibility.stages must be an object")
        stage_visibility = {}

    if set(stage_visibility) != stage_ids:
        fail(
            errors,
            "evidence visibility must have one-to-one stage coverage; "
            f"missing={sorted(stage_ids - set(stage_visibility))} "
            f"extra={sorted(set(stage_visibility) - stage_ids)}",
        )

    for stage_id, contract in stage_visibility.items():
        if not isinstance(contract, dict):
            fail(errors, f"{stage_id}: visibility contract must be an object")
            continue
        required = contract.get("required", [])
        allowed = contract.get("allowed_optional", [])
        excluded = contract.get("excluded", [])
        for field, value in (("required", required), ("allowed_optional", allowed), ("excluded", excluded)):
            ensure_string_list(errors, stage_id, f"visibility.{field}", value)
        if not all(isinstance(value, list) for value in (required, allowed, excluded)):
            continue
        rset, aset, xset = set(required), set(allowed), set(excluded)
        overlap = (rset & aset) | (rset & xset) | (aset & xset)
        if overlap:
            fail(errors, f"{stage_id}: evidence classes overlap across visibility buckets: {sorted(overlap)}")
        partition = rset | aset | xset
        if partition != EVIDENCE_CLASSES:
            fail(
                errors,
                f"{stage_id}: evidence classes must be fully classified; "
                f"missing={sorted(EVIDENCE_CLASSES - partition)} extra={sorted(partition - EVIDENCE_CLASSES)}",
            )
        mode = contract.get("retrieval_mode")
        if mode not in VALID_RETRIEVAL_MODES:
            fail(errors, f"{stage_id}: invalid retrieval_mode {mode!r}")
        disposition = contract.get("output_disposition")
        if disposition not in VALID_OUTPUT_DISPOSITIONS:
            fail(errors, f"{stage_id}: invalid output_disposition {disposition!r}")

    critical_exclusions = {
        "INSTRUCTION_DRAFT": {"PRIVATE_CREATION_DESIGN", "SOLUTION_ORACLE", "VERIFIER_PRIVATE", "PRIOR_REVIEW_RESULTS"},
        "VERIFIER_BUILD": {"SOLUTION_ORACLE"},
        "MODEL_DIAGNOSTIC": {
            "PRIVATE_CREATION_DESIGN",
            "SOLUTION_ORACLE",
            "VERIFIER_PRIVATE",
            "PRIOR_REVIEW_RESULTS",
            "MODEL_TRIAL_EVIDENCE",
        },
    }
    for stage_id, expected in critical_exclusions.items():
        contract = stage_visibility.get(stage_id, {})
        excluded = set(contract.get("excluded", [])) if isinstance(contract, dict) else set()
        missing = expected - excluded
        if missing:
            fail(errors, f"{stage_id}: missing critical evidence exclusions {sorted(missing)}")

    model_contract = stage_visibility.get("MODEL_DIAGNOSTIC", {})
    if isinstance(model_contract, dict) and model_contract.get("retrieval_mode") != "SOLVER_VISIBLE_ONLY":
        fail(errors, "MODEL_DIAGNOSTIC must use SOLVER_VISIBLE_ONLY retrieval mode")

    return str(version), len(stage_visibility), len(declared_classes)


def validate_completion(errors: list[str], stages_by_id: dict[str, dict[str, object]]) -> str:
    completion = load_json(COMPLETION_PATH, errors)
    schema = load_json(COMPLETION_SCHEMA_PATH, errors)
    policy = load_text(COMPLETION_POLICY_PATH, errors)
    creation_pipeline = load_text(CREATION_PIPELINE_PATH, errors)
    creator_registry = load_text(CREATOR_REGISTRY_PATH, errors)

    require_markers(errors, policy, COMPLETION_POLICY_PATH, COMPLETION_POLICY_MARKERS)

    if isinstance(schema, dict):
        if schema.get("$id") != "terminus-stage-contract-completion-v1.2":
            fail(errors, "stage-completion schema must declare $id terminus-stage-contract-completion-v1.2")
        if schema.get("additionalProperties") is not False:
            fail(errors, "stage-completion schema must reject undeclared top-level fields")

    if not isinstance(completion, dict):
        fail(errors, "stage completion overlay must be a JSON object")
        return "?"

    version = completion.get("completion_version")
    if version != "1.2":
        fail(errors, "stage completion overlay must declare completion_version 1.2")

    chain = completion.get("canonical_creation_chain")
    if chain != EXPECTED_CREATION_CHAIN:
        fail(errors, "stage completion canonical_creation_chain does not match required chain")

    phases = completion.get("phase_constraints", {})
    if not isinstance(phases, dict):
        fail(errors, "stage completion phase_constraints must be an object")
        phases = {}

    expected_modes = {
        "SYSTEM_ARCHITECTURE": "DESIGN_ONLY",
        "DEFECT_TOPOLOGY": "PRIVATE_DESIGN",
        "ENVIRONMENT_BUILD": "MATERIALIZATION",
    }
    for stage_id, mode in expected_modes.items():
        phase = phases.get(stage_id)
        if not isinstance(phase, dict):
            fail(errors, f"stage completion missing phase constraint for {stage_id}")
            continue
        if phase.get("execution_mode") != mode:
            fail(errors, f"{stage_id}: expected execution_mode {mode}")

    arch = phases.get("SYSTEM_ARCHITECTURE", {})
    env = phases.get("ENVIRONMENT_BUILD", {})
    defect = phases.get("DEFECT_TOPOLOGY", {})
    if isinstance(arch, dict):
        forbidden = set(arch.get("must_not_consume", []))
        if "DEFECT_TOPOLOGY" not in forbidden:
            fail(errors, "SYSTEM_ARCHITECTURE must not consume DEFECT_TOPOLOGY")
    if isinstance(defect, dict):
        if defect.get("requires_prior") != ["SYSTEM_ARCHITECTURE"]:
            fail(errors, "DEFECT_TOPOLOGY must require prior SYSTEM_ARCHITECTURE")
    if isinstance(env, dict):
        requires = set(env.get("requires_prior", []))
        if requires != {"SYSTEM_ARCHITECTURE", "DEFECT_TOPOLOGY"}:
            fail(errors, "ENVIRONMENT_BUILD must require both SYSTEM_ARCHITECTURE and DEFECT_TOPOLOGY")

    states = completion.get("state_contracts", {})
    freeze = states.get("FROZEN_CANDIDATE") if isinstance(states, dict) else None
    if not isinstance(freeze, dict):
        fail(errors, "stage completion must define FROZEN_CANDIDATE state contract")
    else:
        if freeze.get("entry_from") != "DETERMINISTIC_VALIDATION":
            fail(errors, "FROZEN_CANDIDATE entry_from must be DETERMINISTIC_VALIDATION")
        if freeze.get("exit_to") != "QUALITY_INTERLOCK":
            fail(errors, "FROZEN_CANDIDATE exit_to must be QUALITY_INTERLOCK")
        required_inputs = set(freeze.get("required_inputs", []))
        for field in {
            "CURRENT_TASK_COMMIT",
            "CREATION_RULE_CONTEXT",
            "ORACLE_REWARD",
            "NOP_REWARD",
            "F2P_EMPIRICAL_MATRIX",
            "P2P_EMPIRICAL_MATRIX",
            "UNRESOLVED_POLICY_CONFLICTS",
        }:
            if field not in required_inputs:
                fail(errors, f"FROZEN_CANDIDATE missing required input {field}")

    deterministic = stages_by_id.get("DETERMINISTIC_VALIDATION", {})
    if deterministic.get("success_transition") != "FROZEN_CANDIDATE":
        fail(errors, "DETERMINISTIC_VALIDATION must transition to FROZEN_CANDIDATE")

    required_pipeline_markers = [
        "### 2A. System Architect — clean architecture design",
        "Do not create the broken starter and do not inject defects at this stage",
        "### 2B. Environment Builder — starter materialization",
        "SYSTEM_ARCHITECTURE(design-only) -> DEFECT_TOPOLOGY -> ENVIRONMENT_BUILD(materialization)",
        "### 16. Freeze boundary",
    ]
    require_markers(errors, creation_pipeline, CREATION_PIPELINE_PATH, required_pipeline_markers)

    forbidden_pipeline_markers = [
        "### 2. System Architect / Environment Builder\nBuild the runtime topology",
    ]
    for marker in forbidden_pipeline_markers:
        if marker.lower() in creation_pipeline.lower():
            fail(errors, f"{CREATION_PIPELINE_PATH.relative_to(ROOT)} retains contradictory combined A2 phase")

    required_registry_markers = [
        "two distinct stages with different contracts",
        "Architecture-design invocation (`SYSTEM_ARCHITECTURE`)",
        "Environment-materialization invocation (`ENVIRONMENT_BUILD`)",
        "A2(SYSTEM_ARCHITECTURE design-only) -> A3 -> A2(ENVIRONMENT_BUILD materialization)",
    ]
    require_markers(errors, creator_registry, CREATOR_REGISTRY_PATH, required_registry_markers)

    return str(version)


def main() -> int:
    errors: list[str] = []
    registry = load_json(REGISTRY_PATH, errors)
    schema = load_json(SCHEMA_PATH, errors)
    stage_policy = load_text(STAGE_POLICY_PATH, errors)
    instruction_policy = load_text(INSTRUCTION_POLICY_PATH, errors)
    agent_system = load_text(AGENT_SYSTEM_PATH, errors)

    require_markers(errors, stage_policy, STAGE_POLICY_PATH, STAGE_POLICY_MARKERS)
    require_markers(errors, instruction_policy, INSTRUCTION_POLICY_PATH, INSTRUCTION_POLICY_MARKERS)
    require_markers(errors, agent_system, AGENT_SYSTEM_PATH, AGENT_SYSTEM_BINDING_MARKERS)

    if not re.search(r"Agent-system policy version: `[^`]+`", agent_system):
        fail(errors, "AGENT_SYSTEM.md must declare an Agent-system policy version")

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
    stages_by_id: dict[str, dict[str, object]] = {}
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
            stages_by_id[stage_id] = stage

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

    instruction_stage = stages_by_id.get("INSTRUCTION_DRAFT")
    if isinstance(instruction_stage, dict):
        policy_files = instruction_stage.get("policy_files", [])
        if ".terminus/agents/INSTRUCTION_POLICY.md" not in policy_files:
            fail(errors, "INSTRUCTION_DRAFT must bind .terminus/agents/INSTRUCTION_POLICY.md")
        required_inputs = instruction_stage.get("input_contract", {}).get("required_fields", [])
        for field in [
            "ENGINEERING_OBJECTIVE",
            "REQUIRED_END_STATE",
            "FUNCTIONAL_REQUIREMENTS",
            "REFERENCED_DOCS",
            "REQUIRED_OUTPUTS",
        ]:
            if field not in required_inputs:
                fail(errors, f"INSTRUCTION_DRAFT missing required input contract field {field}")

    visibility_version, visibility_stage_count, evidence_class_count = validate_visibility(errors, id_set)
    completion_version = validate_completion(errors, stages_by_id)

    if errors:
        print("Terminus stage-contract validation FAILED:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("Terminus stage-contract validation PASS")
    print(
        f"contract_version=1.0 visibility_version={visibility_version} completion_version={completion_version} "
        f"stages={len(stages)} visibility_stages={visibility_stage_count} evidence_classes={evidence_class_count} "
        f"required_stages={len(REQUIRED_STAGE_IDS)} instruction_policy=1.0 structured_bindings=present "
        "retrieval_boundaries=classified lifecycle_completion=explicit"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
