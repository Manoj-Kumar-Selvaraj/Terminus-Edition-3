#!/usr/bin/env python3
"""Validate Terminus lifecycle, visibility, and completion stage contracts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
A = T / "agents"

REGISTRY = A / "stage_contracts.json"
REGISTRY_SCHEMA = A / "schemas" / "stage_contracts.schema.json"
VISIBILITY = A / "evidence_visibility.json"
VISIBILITY_SCHEMA = A / "schemas" / "evidence_visibility.schema.json"
VISIBILITY_POLICY = A / "EVIDENCE_VISIBILITY.md"
COMPLETION = A / "stage_contract_completion.json"
COMPLETION_SCHEMA = A / "schemas" / "stage_contract_completion.schema.json"
COMPLETION_POLICY = A / "STAGE_CONTRACT_COMPLETION.md"
A2_PHASE_PROMPTS = A / "A2_PHASE_PROMPTS.md"
STAGE_POLICY = A / "STAGE_CONTRACTS.md"
INSTRUCTION_POLICY = A / "INSTRUCTION_POLICY.md"
CREATION_PIPELINE = A / "CREATION_PIPELINE.md"
CREATOR_REGISTRY = A / "CREATOR_AGENT_REGISTRY.md"
AGENT_SYSTEM = T / "AGENT_SYSTEM.md"

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

EXPECTED_CHAIN = [
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
VALID_RETRIEVAL_MODES = {"EXACT_ONLY", "FILTERED_HYBRID", "SOLVER_VISIBLE_ONLY", "EXTERNAL_BOUND"}
VALID_OUTPUT_DISPOSITIONS = {
    "EPHEMERAL",
    "DURABLE_CONTROL_PLANE",
    "PRIVATE_CONTROL_PLANE",
    "TASK_ARTIFACT",
    "REVIEW_EVIDENCE",
    "EXTERNAL_EVIDENCE",
}
NON_STAGE_TRANSITIONS = {"FROZEN_CANDIDATE", "END"}


def load_json(path: Path, errors: list[str]) -> dict:
    if not path.is_file():
        errors.append(f"missing required file: {path.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(ROOT)} must contain a JSON object")
        return {}
    return value


def load_text(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"missing required file: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def require_markers(errors: list[str], text: str, path: Path, markers: list[str]) -> None:
    lower = text.lower()
    for marker in markers:
        if marker.lower() not in lower:
            errors.append(f"{path.relative_to(ROOT)} missing required marker: {marker}")


def string_list(errors: list[str], where: str, value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        errors.append(f"{where} must be a list of strings")
        return []
    if len(value) != len(set(value)):
        errors.append(f"{where} contains duplicate values")
    return value


def validate_base(errors: list[str]) -> tuple[dict[str, dict], str]:
    registry = load_json(REGISTRY, errors)
    schema = load_json(REGISTRY_SCHEMA, errors)

    if registry.get("contract_version") != "1.0":
        errors.append("stage contract registry must declare contract_version 1.0")
    if schema.get("$id") != "terminus-stage-contracts-v1":
        errors.append("stage-contract schema must declare $id terminus-stage-contracts-v1")
    if schema.get("additionalProperties") is not False:
        errors.append("stage-contract schema must reject undeclared top-level fields")

    raw_stages = registry.get("stages")
    if not isinstance(raw_stages, list):
        errors.append("stage contract registry 'stages' must be a list")
        raw_stages = []

    stages: dict[str, dict] = {}
    for index, stage in enumerate(raw_stages):
        if not isinstance(stage, dict):
            errors.append(f"stage[{index}] must be an object")
            continue
        stage_id = stage.get("id")
        if not isinstance(stage_id, str) or not stage_id:
            errors.append(f"stage[{index}] missing valid id")
            continue
        if stage_id in stages:
            errors.append(f"duplicate stage id {stage_id}")
        stages[stage_id] = stage

        missing = REQUIRED_STAGE_KEYS - set(stage)
        extra = set(stage) - REQUIRED_STAGE_KEYS
        if missing:
            errors.append(f"{stage_id}: missing stage keys {sorted(missing)}")
        if extra:
            errors.append(f"{stage_id}: undeclared stage keys {sorted(extra)}")
        if stage.get("lifecycle") not in VALID_LIFECYCLES:
            errors.append(f"{stage_id}: invalid lifecycle {stage.get('lifecycle')!r}")
        if stage.get("role_class") not in VALID_ROLE_CLASSES:
            errors.append(f"{stage_id}: invalid role_class {stage.get('role_class')!r}")
        if not isinstance(stage.get("owner"), str) or not stage.get("owner", "").strip():
            errors.append(f"{stage_id}: owner must be non-empty")

        for field in ("policy_files", "prompt_files", "evidence_required", "deterministic_validators", "semantic_reviewers", "stale_on"):
            string_list(errors, f"{stage_id}.{field}", stage.get(field))

        for field in ("policy_files", "prompt_files"):
            refs = stage.get(field)
            if not isinstance(refs, list):
                continue
            for ref in refs:
                if isinstance(ref, str) and (ref.startswith(".terminus/") or ref == "TERMINUS_3_AI_INSTRUCTIONS.md"):
                    if not (ROOT / ref).exists():
                        errors.append(f"{stage_id}.{field} references missing file {ref}")

        inputs = stage.get("input_contract")
        if not isinstance(inputs, dict) or set(inputs) != {"required_fields", "optional_fields"}:
            errors.append(f"{stage_id}.input_contract must contain required_fields and optional_fields only")
        else:
            string_list(errors, f"{stage_id}.input_contract.required_fields", inputs.get("required_fields"))
            string_list(errors, f"{stage_id}.input_contract.optional_fields", inputs.get("optional_fields"))

        outputs = stage.get("output_contract")
        expected_output_keys = {"status_values", "required_fields", "optional_fields", "persisted_artifacts"}
        if not isinstance(outputs, dict) or set(outputs) != expected_output_keys:
            errors.append(f"{stage_id}.output_contract must contain only {sorted(expected_output_keys)}")
        else:
            for field in expected_output_keys:
                values = string_list(errors, f"{stage_id}.output_contract.{field}", outputs.get(field))
                if field in {"status_values", "required_fields"} and not values:
                    errors.append(f"{stage_id}.output_contract.{field} cannot be empty")

        routes = stage.get("failure_routes")
        if not isinstance(routes, dict) or any(not isinstance(k, str) or not k or not isinstance(v, str) or not v.strip() for k, v in routes.items()):
            errors.append(f"{stage_id}.failure_routes must map non-empty strings to non-empty strings")

    missing = REQUIRED_STAGE_IDS - set(stages)
    if missing:
        errors.append(f"stage registry missing required stages {sorted(missing)}")

    known_targets = set(stages) | NON_STAGE_TRANSITIONS
    for stage_id, stage in stages.items():
        transition = stage.get("success_transition")
        if transition not in known_targets:
            errors.append(f"{stage_id}: unknown success_transition {transition!r}")

    instruction = stages.get("INSTRUCTION_DRAFT", {})
    if ".terminus/agents/INSTRUCTION_POLICY.md" not in instruction.get("policy_files", []):
        errors.append("INSTRUCTION_DRAFT must bind INSTRUCTION_POLICY.md")
    required_inputs = set(instruction.get("input_contract", {}).get("required_fields", []))
    for field in {"ENGINEERING_OBJECTIVE", "REQUIRED_END_STATE", "FUNCTIONAL_REQUIREMENTS", "REFERENCED_DOCS", "REQUIRED_OUTPUTS"}:
        if field not in required_inputs:
            errors.append(f"INSTRUCTION_DRAFT missing required input {field}")

    return stages, str(registry.get("contract_version", "?"))


def validate_visibility(errors: list[str], stage_ids: set[str]) -> tuple[str, int, int]:
    visibility = load_json(VISIBILITY, errors)
    schema = load_json(VISIBILITY_SCHEMA, errors)
    policy = load_text(VISIBILITY_POLICY, errors)

    require_markers(errors, policy, VISIBILITY_POLICY, [
        "Evidence visibility policy version: `1.1`",
        "required evidence",
        "allowed optional evidence",
        "excluded evidence",
        "retrieval",
        "RAG",
    ])

    if visibility.get("visibility_version") != "1.1":
        errors.append("evidence visibility registry must declare visibility_version 1.1")
    if schema.get("$id") != "terminus-evidence-visibility-v1.1":
        errors.append("evidence-visibility schema must declare $id terminus-evidence-visibility-v1.1")

    classes = visibility.get("evidence_classes")
    if not isinstance(classes, dict) or set(classes) != EVIDENCE_CLASSES:
        actual = set(classes) if isinstance(classes, dict) else set()
        errors.append(f"evidence classes mismatch missing={sorted(EVIDENCE_CLASSES-actual)} extra={sorted(actual-EVIDENCE_CLASSES)}")
        classes = {}

    entries = visibility.get("stages")
    if not isinstance(entries, dict):
        errors.append("evidence_visibility.stages must be an object")
        entries = {}
    if set(entries) != stage_ids:
        errors.append(f"evidence visibility stage coverage mismatch missing={sorted(stage_ids-set(entries))} extra={sorted(set(entries)-stage_ids)}")

    for stage_id, contract in entries.items():
        if not isinstance(contract, dict):
            errors.append(f"{stage_id}: visibility contract must be object")
            continue
        required = set(string_list(errors, f"{stage_id}.visibility.required", contract.get("required")))
        allowed = set(string_list(errors, f"{stage_id}.visibility.allowed_optional", contract.get("allowed_optional")))
        excluded = set(string_list(errors, f"{stage_id}.visibility.excluded", contract.get("excluded")))
        if (required & allowed) or (required & excluded) or (allowed & excluded):
            errors.append(f"{stage_id}: visibility buckets overlap")
        if required | allowed | excluded != EVIDENCE_CLASSES:
            errors.append(f"{stage_id}: every evidence class must be classified exactly once")
        if contract.get("retrieval_mode") not in VALID_RETRIEVAL_MODES:
            errors.append(f"{stage_id}: invalid retrieval_mode {contract.get('retrieval_mode')!r}")
        if contract.get("output_disposition") not in VALID_OUTPUT_DISPOSITIONS:
            errors.append(f"{stage_id}: invalid output_disposition {contract.get('output_disposition')!r}")

    critical = {
        "INSTRUCTION_DRAFT": {"PRIVATE_CREATION_DESIGN", "SOLUTION_ORACLE", "VERIFIER_PRIVATE", "PRIOR_REVIEW_RESULTS"},
        "VERIFIER_BUILD": {"SOLUTION_ORACLE"},
        "MODEL_DIAGNOSTIC": {"PRIVATE_CREATION_DESIGN", "SOLUTION_ORACLE", "VERIFIER_PRIVATE", "PRIOR_REVIEW_RESULTS", "MODEL_TRIAL_EVIDENCE"},
    }
    for stage_id, required_exclusions in critical.items():
        contract = entries.get(stage_id, {})
        excluded = set(contract.get("excluded", [])) if isinstance(contract, dict) else set()
        missing = required_exclusions - excluded
        if missing:
            errors.append(f"{stage_id}: missing critical exclusions {sorted(missing)}")

    if isinstance(entries.get("MODEL_DIAGNOSTIC"), dict) and entries["MODEL_DIAGNOSTIC"].get("retrieval_mode") != "SOLVER_VISIBLE_ONLY":
        errors.append("MODEL_DIAGNOSTIC must use SOLVER_VISIBLE_ONLY retrieval mode")

    return str(visibility.get("visibility_version", "?")), len(entries), len(classes)


def validate_completion(errors: list[str], stages: dict[str, dict]) -> str:
    completion = load_json(COMPLETION, errors)
    schema = load_json(COMPLETION_SCHEMA, errors)
    policy = load_text(COMPLETION_POLICY, errors)
    pipeline = load_text(CREATION_PIPELINE, errors)
    registry_text = load_text(CREATOR_REGISTRY, errors)
    phase_prompts = load_text(A2_PHASE_PROMPTS, errors)

    require_markers(errors, policy, COMPLETION_POLICY, [
        "Completion policy version: `1.2`",
        "A2 two-phase contract",
        "SYSTEM_ARCHITECTURE",
        "ENVIRONMENT_BUILD",
        "Freeze-state contract",
        "FROZEN_CANDIDATE",
        "Canonical creation chain",
    ])
    require_markers(errors, phase_prompts, A2_PHASE_PROMPTS, [
        "A2 phase prompt policy version: `1.0`",
        "`SYSTEM_ARCHITECTURE` — A2 System Architect",
        "`ENVIRONMENT_BUILD` — A2 Environment Builder",
        "not starter materialization",
        "Inject **only** the approved A3 defect/incomplete-behavior topology",
    ])

    if completion.get("completion_version") != "1.2":
        errors.append("stage completion overlay must declare completion_version 1.2")
    if schema.get("$id") != "terminus-stage-contract-completion-v1.2":
        errors.append("stage-completion schema must declare $id terminus-stage-contract-completion-v1.2")
    if completion.get("canonical_creation_chain") != EXPECTED_CHAIN:
        errors.append("stage completion canonical_creation_chain does not match required chain")

    phases = completion.get("phase_constraints")
    if not isinstance(phases, dict):
        errors.append("stage completion phase_constraints must be an object")
        phases = {}

    expected = {
        "SYSTEM_ARCHITECTURE": ("DESIGN_ONLY", {"WORK_PACKAGE_RESEARCH"}),
        "DEFECT_TOPOLOGY": ("PRIVATE_DESIGN", {"SYSTEM_ARCHITECTURE"}),
        "ENVIRONMENT_BUILD": ("MATERIALIZATION", {"SYSTEM_ARCHITECTURE", "DEFECT_TOPOLOGY"}),
    }
    for stage_id, (mode, prior) in expected.items():
        phase = phases.get(stage_id)
        if not isinstance(phase, dict):
            errors.append(f"missing phase constraint for {stage_id}")
            continue
        if phase.get("execution_mode") != mode:
            errors.append(f"{stage_id}: expected execution_mode {mode}")
        if set(phase.get("requires_prior", [])) != prior:
            errors.append(f"{stage_id}: requires_prior must be {sorted(prior)}")
        prompt = phase.get("phase_prompt_file")
        if not isinstance(prompt, str) or not prompt:
            errors.append(f"{stage_id}: phase_prompt_file is required")
        elif not (ROOT / prompt).is_file():
            errors.append(f"{stage_id}: phase_prompt_file does not exist: {prompt}")

    for stage_id in ("SYSTEM_ARCHITECTURE", "ENVIRONMENT_BUILD"):
        phase = phases.get(stage_id, {})
        if isinstance(phase, dict) and phase.get("phase_prompt_file") != ".terminus/agents/A2_PHASE_PROMPTS.md":
            errors.append(f"{stage_id}: must use .terminus/agents/A2_PHASE_PROMPTS.md")

    arch = phases.get("SYSTEM_ARCHITECTURE", {})
    if isinstance(arch, dict) and "DEFECT_TOPOLOGY" not in set(arch.get("must_not_consume", [])):
        errors.append("SYSTEM_ARCHITECTURE must not consume DEFECT_TOPOLOGY")

    freeze_states = completion.get("state_contracts")
    freeze = freeze_states.get("FROZEN_CANDIDATE") if isinstance(freeze_states, dict) else None
    if not isinstance(freeze, dict):
        errors.append("completion overlay must define FROZEN_CANDIDATE")
    else:
        if freeze.get("entry_from") != "DETERMINISTIC_VALIDATION":
            errors.append("FROZEN_CANDIDATE entry_from must be DETERMINISTIC_VALIDATION")
        if freeze.get("exit_to") != "QUALITY_INTERLOCK":
            errors.append("FROZEN_CANDIDATE exit_to must be QUALITY_INTERLOCK")
        required = set(freeze.get("required_inputs", []))
        for field in {"CURRENT_TASK_COMMIT", "CREATION_RULE_CONTEXT", "ORACLE_REWARD", "NOP_REWARD", "F2P_EMPIRICAL_MATRIX", "P2P_EMPIRICAL_MATRIX", "UNRESOLVED_POLICY_CONFLICTS"}:
            if field not in required:
                errors.append(f"FROZEN_CANDIDATE missing required input {field}")

    if stages.get("DETERMINISTIC_VALIDATION", {}).get("success_transition") != "FROZEN_CANDIDATE":
        errors.append("DETERMINISTIC_VALIDATION must transition to FROZEN_CANDIDATE")

    require_markers(errors, pipeline, CREATION_PIPELINE, [
        "### 2A. System Architect — clean architecture design",
        "Do not create the broken starter and do not inject defects at this stage",
        "### 2B. Environment Builder — starter materialization",
        "SYSTEM_ARCHITECTURE(design-only) -> DEFECT_TOPOLOGY -> ENVIRONMENT_BUILD(materialization)",
        "### 16. Freeze boundary",
    ])
    require_markers(errors, registry_text, CREATOR_REGISTRY, [
        "two distinct stages with different contracts",
        "Architecture-design invocation (`SYSTEM_ARCHITECTURE`)",
        "Environment-materialization invocation (`ENVIRONMENT_BUILD`)",
        "A2(SYSTEM_ARCHITECTURE design-only) -> A3 -> A2(ENVIRONMENT_BUILD materialization)",
    ])

    return str(completion.get("completion_version", "?"))


def main() -> int:
    errors: list[str] = []

    agent_system = load_text(AGENT_SYSTEM, errors)
    stage_policy = load_text(STAGE_POLICY, errors)
    instruction_policy = load_text(INSTRUCTION_POLICY, errors)

    require_markers(errors, agent_system, AGENT_SYSTEM, [
        "Structured execution bindings",
        ".terminus/agents/stage_contracts.json",
        ".terminus/agents/STAGE_CONTRACTS.md",
        ".terminus/agents/INSTRUCTION_POLICY.md",
        "INPUT CONTRACT",
        "OUTPUT CONTRACT",
        "DETERMINISTIC VALIDATORS",
        "SEMANTIC REVIEWERS",
        "FAILURE ROUTES",
        "SUCCESS TRANSITION",
        "STALE_ON",
    ])
    if not re.search(r"Agent-system policy version: `[^`]+`", agent_system):
        errors.append("AGENT_SYSTEM.md must declare an Agent-system policy version")

    require_markers(errors, stage_policy, STAGE_POLICY, [
        "Stage-contract policy version: `1.0`",
        "Canonical stage fields",
        "Validator honesty rule",
        "Input/output contract rule",
        "Runtime prompt projection",
        "Section-to-stage bindings",
        "Failure routing principle",
        "Staleness principle",
    ])
    require_markers(errors, instruction_policy, INSTRUCTION_POLICY, [
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
    ])

    stages, contract_version = validate_base(errors)
    visibility_version, visibility_stage_count, evidence_class_count = validate_visibility(errors, set(stages))
    completion_version = validate_completion(errors, stages)

    if errors:
        print("Terminus stage-contract validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Terminus stage-contract validation PASS")
    print(
        f"contract_version={contract_version} visibility_version={visibility_version} completion_version={completion_version} "
        f"stages={len(stages)} visibility_stages={visibility_stage_count} evidence_classes={evidence_class_count} "
        f"required_stages={len(REQUIRED_STAGE_IDS)} instruction_policy=1.0 structured_bindings=present "
        "retrieval_boundaries=classified lifecycle_completion=explicit phase_prompts=bound freeze_state=explicit"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
